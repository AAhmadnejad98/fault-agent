import logging
import sys

from faultagent import config
from faultagent.agent import ask
from faultagent.data import connect, get_collection


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('usage: python ask.py "Why does F07 keep tripping?"')
    if "-v" in sys.argv:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    question = " ".join(a for a in sys.argv[1:] if a != "-v")
    conn = connect(config.DB_PATH)
    result = ask(question, conn, get_collection(config.CHROMA_PATH))
    a = result.answer

    print(f"\nQ: {result.question}")
    print(f"A: {a.answer if a else '(no valid answer)'}")
    if a and a.cause:
        print(f"Cause: {a.cause}")
    if a and a.events:
        print("Events:")
        for e in a.events:
            print(f"  {e.time}  {e.device}  {e.alarm}  {e.current_a:g} A")
    if a:
        print(f"Sources: {', '.join(a.sources) or '-'}  |  confidence: {a.confidence}")
    print(f"Notes retrieved: {result.notes}  |  tools called: {result.tools}")
    if result.escalated:
        print("Status: ESCALATED -> " + "; ".join(result.reasons))
    else:
        print("Status: OK, all checks passed")
    print(f"Trace: {result.trace_id}  (python show_trace.py {result.trace_id})\n")


if __name__ == "__main__":
    main()
