import logging
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from faultagent import config
from faultagent.agent import ask
from faultagent.data import connect, get_collection
from faultagent.models import Result
from faultagent.trace import load

app = FastAPI(title="fault-agent")
log = logging.getLogger("uvicorn.error")
client = anthropic.Anthropic()
collection = get_collection(config.CHROMA_PATH)
PAGE = Path(__file__).parent / "static" / "index.html"


class Question(BaseModel):
    question: str


@app.get("/")
def index():
    return FileResponse(PAGE)


@app.post("/ask", response_model=Result)
def ask_question(q: Question):
    text = q.question.strip()
    if not text:
        raise HTTPException(400, "empty question")
    conn = connect(config.DB_PATH)
    try:
        return ask(text, conn, collection, client)
    except anthropic.APIError as err:
        log.exception("anthropic error")
        raise HTTPException(502, f"LLM API error: {err.message}")
    except Exception as err:
        log.exception("ask failed")
        raise HTTPException(500, f"{type(err).__name__}: {err}")
    finally:
        conn.close()


@app.get("/trace/{trace_id}")
def get_trace(trace_id: str):
    conn = connect(config.DB_PATH)
    try:
        steps = load(conn, trace_id)
    finally:
        conn.close()
    if not steps:
        raise HTTPException(404, "trace not found")
    return steps
