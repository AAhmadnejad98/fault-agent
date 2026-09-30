import os
from pathlib import Path

import pandas as pd
import pytest

from faultagent.agent import ask
from faultagent.data import build_all, connect, get_collection

ROOT = Path(__file__).resolve().parents[1]
CASES = pd.read_csv(ROOT / "tests/test_set.csv", dtype=str, keep_default_na=False).to_dict("records")

pytestmark = pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("eval")
    build_all(str(ROOT / "data/faults.csv"), str(tmp / "grid.db"), str(tmp / "chroma"))
    conn = connect(str(tmp / "grid.db"))
    col = get_collection(str(tmp / "chroma"))
    return [(case, ask(case["question"], conn, col)) for case in CASES]


def score(results, name, grade) -> float:
    graded = [g for g in (grade(c, r) for c, r in results) if g is not None]
    value = sum(graded) / len(graded)
    print(f"\n{name}: {sum(graded)}/{len(graded)} = {value:.0%}")
    return value


def grade_retrieval(case, res):
    if not case["expected_notes"]:
        return None
    return {int(i) for i in case["expected_notes"].split(";")} <= set(res.notes)


def grade_tool(case, res):
    if not case["expected_tool"]:
        return None
    return case["expected_tool"] in res.tools


def grade_answer(case, res):
    if not case["expected_text"]:
        return None
    a = res.answer
    text = f"{a.answer} {a.cause or ''}".lower() if a else ""
    return case["expected_text"].lower() in text


def grade_escalation(case, res):
    return res.escalated == (case["should_escalate"] == "yes")


def test_retrieval(results):
    assert score(results, "retrieval@3", grade_retrieval) >= 0.8


def test_tool_choice(results):
    assert score(results, "tool choice", grade_tool) >= 0.8


def test_answer(results):
    assert score(results, "answer", grade_answer) >= 0.8


def test_escalation(results):
    assert score(results, "escalation", grade_escalation) >= 0.8
