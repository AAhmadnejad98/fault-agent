import json
import sys

from faultagent import config
from faultagent.data import connect
from faultagent.trace import load

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python show_trace.py <trace_id>")
    steps = load(connect(config.DB_PATH), sys.argv[1])
    if not steps:
        sys.exit("trace not found")
    for s in steps:
        print(f"--- #{s['step']} {s['kind']}")
        print(json.dumps(s["payload"], indent=2))
