import json
import sqlite3

import anthropic

from . import config
from .checks import escalation_reasons, validate
from .models import Result
from .retrieval import search_notes
from .tools import TOOLS, run_tool
from .trace import Trace

SYSTEM = """You are a fault diagnosis assistant for grid operators.
Rules:
- Get every number and event from the tools. Never guess a number.
- Use the operator notes to explain causes and cite them as note:<id>.
- Cite every tool you used as tool:<name>.
- Copy times, alarms and currents exactly as the tools return them.
- Write currents as plain numbers followed by A, e.g. 1320 A.
- If the data does not answer the question, say so and set escalate to true.
- Always finish by calling give_answer."""


def build_prompt(question: str, notes: list[dict]) -> str:
    if notes:
        lines = "\n".join(f"[note:{n['note_id']}] ({n['device']}, {n['alarm']}) {n['text']}" for n in notes)
    else:
        lines = "(no matching notes)"
    return f"Question: {question}\n\nOperator notes:\n{lines}"


def run_loop(client, conn: sqlite3.Connection, messages: list, trace: Trace):
    calls, rows = [], []
    for _ in range(config.MAX_STEPS):
        resp = client.messages.create(
            model=config.MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        results, final = [], None
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "give_answer":
                final = block.input
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": "received"})
                continue
            out = run_tool(conn, block.name, block.input)
            calls.append(block.name)
            rows.extend(out)
            trace.log("tool", {"name": block.name, "input": block.input, "rows": out})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})

        if not results:
            messages.append({"role": "user", "content": [{"type": "text", "text": "Finish by calling give_answer."}]})
            continue
        messages.append({"role": "user", "content": results})
        if final is not None:
            trace.log("answer", final)
            return final, calls, rows
    return None, calls, rows


def ask(question: str, conn: sqlite3.Connection, collection, client=None) -> Result:
    client = client or anthropic.Anthropic()
    trace = Trace(conn)
    trace.log("question", question)

    notes = search_notes(collection, question)
    trace.log("retrieval", notes)
    note_ids = {n["note_id"] for n in notes}
    messages = [{"role": "user", "content": build_prompt(question, notes)}]

    calls, rows, answer, problems = [], [], None, []
    for attempt in range(2):
        raw, new_calls, new_rows = run_loop(client, conn, messages, trace)
        calls += new_calls
        rows += new_rows
        answer, problems = validate(raw, rows, note_ids, calls)
        trace.log("checks", {"attempt": attempt + 1, "problems": problems})
        if not problems:
            break
        # one retry with the failed checks as feedback
        feedback = "Your answer failed these checks. Fix them and call give_answer again:\n" + "\n".join(problems)
        messages[-1]["content"].append({"type": "text", "text": feedback})

    reasons = [f"check failed: {p}" for p in problems] if problems else escalation_reasons(answer, rows)
    result = Result(
        question=question,
        answer=answer,
        escalated=bool(reasons),
        reasons=reasons,
        notes=sorted(note_ids),
        tools=calls,
        trace_id=trace.id,
    )
    trace.log("result", result.model_dump())
    return result
