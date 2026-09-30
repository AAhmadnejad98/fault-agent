import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

log = logging.getLogger("faultagent")


class Trace:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.id = uuid.uuid4().hex[:12]
        self.step = 0
        conn.execute("CREATE TABLE IF NOT EXISTS traces (trace_id TEXT, step INTEGER, kind TEXT, payload TEXT, created TEXT)")

    def log(self, kind: str, payload) -> None:
        self.step += 1
        data = json.dumps(payload, default=str)
        self.conn.execute(
            "INSERT INTO traces VALUES (?, ?, ?, ?, ?)",
            (self.id, self.step, kind, data, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        log.info("%s #%d %s", self.id, self.step, kind)


def load(conn: sqlite3.Connection, trace_id: str) -> list[dict]:
    sql = "SELECT step, kind, payload FROM traces WHERE trace_id = ? ORDER BY step"
    return [{"step": s, "kind": k, "payload": json.loads(p)} for s, k, p in conn.execute(sql, (trace_id,))]
