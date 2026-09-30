import sqlite3


def get_alarms(conn: sqlite3.Connection, device: str) -> list[dict]:
    sql = "SELECT * FROM measurements WHERE device = ? ORDER BY time"
    return [dict(r) for r in conn.execute(sql, (device.upper(),))]


def get_current(conn: sqlite3.Connection, device: str, time: str) -> list[dict]:
    sql = "SELECT * FROM measurements WHERE device = ? AND time LIKE ? ORDER BY time"
    return [dict(r) for r in conn.execute(sql, (device.upper(), f"%{time}"))]


def get_by_substation(conn: sqlite3.Connection, substation: str) -> list[dict]:
    sql = "SELECT * FROM measurements WHERE lower(substation) = lower(?) ORDER BY time"
    return [dict(r) for r in conn.execute(sql, (substation,))]


FUNCS = {"get_alarms": get_alarms, "get_current": get_current, "get_by_substation": get_by_substation}


def run_tool(conn: sqlite3.Connection, name: str, args: dict) -> list[dict]:
    fn = FUNCS.get(name)
    if fn is None:
        return []
    try:
        return fn(conn, **args)
    except TypeError:
        return []


TOOLS = [
    {
        "name": "get_alarms",
        "description": "All events for one device: time, substation, current, voltage and alarm. Use for questions about a single device.",
        "input_schema": {
            "type": "object",
            "properties": {"device": {"type": "string", "description": "Device id, e.g. F07"}},
            "required": ["device"],
        },
    },
    {
        "name": "get_current",
        "description": "Measured current of one device at a given time. Use when the question names a time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device id, e.g. F12"},
                "time": {"type": "string", "description": "HH:MM or YYYY-MM-DD HH:MM"},
            },
            "required": ["device", "time"],
        },
    },
    {
        "name": "get_by_substation",
        "description": "All events in one substation. Use when the question is about a substation, not a single device.",
        "input_schema": {
            "type": "object",
            "properties": {"substation": {"type": "string", "description": "North, South, East or West"}},
            "required": ["substation"],
        },
    },
    {
        "name": "give_answer",
        "description": "Return the final answer to the operator. Always finish with this tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "Short answer for the operator"},
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "time": {"type": "string"},
                            "device": {"type": "string"},
                            "alarm": {"type": "string"},
                            "current_a": {"type": "number"},
                        },
                        "required": ["time", "device", "alarm", "current_a"],
                    },
                },
                "cause": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "escalate": {"type": "boolean"},
            },
            "required": ["answer", "sources", "confidence", "escalate"],
        },
    },
]
