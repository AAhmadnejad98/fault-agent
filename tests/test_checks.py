from faultagent.checks import check, escalation_reasons
from faultagent.models import Answer, Event

ROWS = [
    {"id": 3, "time": "2026-03-14 11:40", "device": "F07", "substation": "North", "current_a": 1320.0, "voltage_kv": 19.5, "alarm": "OC_TRIP"},
    {"id": 6, "time": "2026-03-14 17:30", "device": "F07", "substation": "North", "current_a": 1400.0, "voltage_kv": 19.6, "alarm": "OC_TRIP"},
]


def make(current: float) -> Answer:
    return Answer(
        answer=f"F07 tripped at 11:40 with {current:g} A.",
        events=[Event(time="2026-03-14 11:40", device="F07", alarm="OC_TRIP", current_a=current)],
        sources=["note:3", "tool:get_alarms"],
        confidence="high",
    )


def test_correct_answer_passes():
    assert check(make(1320), ROWS, {3, 6}, ["get_alarms"]) == []


def test_wrong_current_is_caught():
    problems = check(make(1520), ROWS, {3, 6}, ["get_alarms"])
    assert any("1520" in p for p in problems)


def test_unknown_source_is_caught():
    answer = make(1320)
    answer.sources.append("note:9")
    assert check(answer, ROWS, {3, 6}, ["get_alarms"]) == ["unknown source: note:9"]


def test_critical_fault_escalates():
    rows = [{**ROWS[0], "device": "B2", "alarm": "BREAKER_FAIL", "current_a": 0.0}]
    reasons = escalation_reasons(Answer(answer="Breaker failed.", confidence="high"), rows)
    assert any("BREAKER_FAIL" in r for r in reasons)


def test_no_data_escalates():
    reasons = escalation_reasons(Answer(answer="No data for F99.", confidence="low"), [])
    assert "no data returned by tools" in reasons
