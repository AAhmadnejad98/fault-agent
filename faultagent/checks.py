import re

from pydantic import ValidationError

from . import config
from .models import Answer, Event

AMPS = re.compile(r"(\d+(?:\.\d+)?)\s?(?:A|amps?)\b")


def _same(e: Event, row: dict) -> bool:
    return (
        row["device"] == e.device.upper()
        and row["alarm"] == e.alarm
        and row["time"].endswith(e.time)
        and float(row["current_a"]) == e.current_a
    )


def check(answer: Answer, rows: list[dict], note_ids: set[int], calls: list[str]) -> list[str]:
    problems = []
    for e in answer.events:
        if not any(_same(e, r) for r in rows):
            problems.append(f"event not in tool results: {e.time} {e.device} {e.alarm} {e.current_a:g} A")

    currents = {float(r["current_a"]) for r in rows}
    for value in AMPS.findall(answer.answer):
        if float(value) not in currents:
            problems.append(f"current {value} A not in tool results")

    allowed = {f"note:{i}" for i in note_ids} | {f"tool:{c}" for c in calls}
    for s in answer.sources:
        if s not in allowed:
            problems.append(f"unknown source: {s}")
    return problems


def validate(raw: dict | None, rows: list[dict], note_ids: set[int], calls: list[str]) -> tuple[Answer | None, list[str]]:
    if raw is None:
        return None, ["no final answer"]
    try:
        answer = Answer.model_validate(raw)
    except ValidationError as err:
        return None, [f"format: {'.'.join(map(str, e['loc']))} {e['msg']}" for e in err.errors()]
    return answer, check(answer, rows, note_ids, calls)


def escalation_reasons(answer: Answer, rows: list[dict]) -> list[str]:
    reasons = []
    if answer.escalate:
        reasons.append("model asked for a specialist")
    if answer.confidence == "low":
        reasons.append("low confidence")
    if not rows:
        reasons.append("no data returned by tools")
    critical = {r["alarm"] for r in rows} & config.CRITICAL
    if critical:
        reasons.append(f"critical fault: {', '.join(sorted(critical))}")
    return reasons
