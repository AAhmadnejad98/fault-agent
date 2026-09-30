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
