# fault-agent

   **Live demo:** https://fault-agent-xxxx.onrender.com (free tier, first load may take ~50 s)
   
A small, runnable reference implementation of an LLM agent that answers operator questions about grid faults, and checks its own answers before anyone sees them.

It mirrors the design of a production system I built for grid operators: RAG over operator notes, tool use for exact numbers, structured output, code-level validation, escalation to a human, full tracing, and an evaluation set. The data here is a small synthetic sample, not production data.

## How it works

```
CSV ─► pandas (clean, split) ─┬─► numbers ─► SQLite ◄──────── tools ◄─┐
                              └─► notes ─► embeddings ─► ChromaDB      │
                                                            │          │
question ─► search notes (top-k) ─► Claude (Anthropic SDK) ─┴── tool use
                                        │
                              give_answer (JSON) ─► Pydantic ─► checks
                                                                  │
                                              pass ─► answer + sources
                                              fail ─► retry once ─► escalate
                        every step ─► traces table (SQLite)
```

- **Numbers never go through the prompt as text.** Claude asks for a tool, our code runs a fixed SQL query, and Claude only sees the exact rows.
- **Text is searched by meaning.** Operator notes are chunked, embedded and stored in ChromaDB, filtered by device or substation when the question names one.
- **Every answer is checked by code.** Each event and current in the answer must exist in the tool results, and every cited source must have actually been retrieved or called.
- **Escalation.** Failed checks after one retry, low confidence, no data or a critical alarm (`BREAKER_FAIL`) all go to a specialist.
- **Tracing.** Each question gets a trace id; retrieval, tool calls, the answer and check results are stored and can be replayed.

## Setup (Ubuntu / WSL)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...        # optional
```

Embeddings use OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set. Without it, ChromaDB's local default model is used (downloaded on first run). The Claude model can be changed with `CLAUDE_MODEL`.

## Run

```bash
python build.py
python ask.py "Why does F07 keep tripping?"
python ask.py "Why did F99 trip?"
python show_trace.py <trace_id>
```

Add `-v` to `ask.py` to log each step as it happens.

## Web UI

```bash
uvicorn server:app --reload
```

Open http://localhost:8000, ask a question and see the answer, the verified events, sources, status and the full trace. The API is `POST /ask` with `{"question": "..."}` and `GET /trace/{id}`.

## Tests

```bash
python -m pytest tests/test_checks.py -v      # offline, no API calls
python -m pytest tests/test_eval.py -s        # full evaluation, uses the API
```

The evaluation runs `tests/test_set.csv` through the whole pipeline, including trap questions (unknown device, off-topic), and scores four things separately: retrieval@3, tool choice, answer correctness and escalation.

## Layout

```
data/faults.csv          raw sample data (inconsistent alarm names, one duplicate)
faultagent/data.py       cleaning, split, SQLite, chunking, embeddings, ChromaDB
faultagent/retrieval.py  note search with metadata filters
faultagent/tools.py      fixed SQL tools and tool schemas
faultagent/models.py     Pydantic output models
faultagent/checks.py     validation and escalation rules
faultagent/trace.py      tracing to SQLite
faultagent/agent.py      the agent loop
server.py                FastAPI app: /ask, /trace/{id} and the web page
static/index.html        single-page UI
tests/                   unit tests for the checks and the evaluation set
```

## Why no framework

The pipeline is built directly on the Anthropic and OpenAI SDKs, ChromaDB and Pydantic. With a small tool set, writing the loop by hand keeps every step visible, which makes validation and tracing straightforward. LlamaIndex would cover the retrieval part and LangGraph the agent loop and escalation branches.
