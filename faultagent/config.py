import os

CSV_PATH = "data/faults.csv"
DB_PATH = "grid.db"
CHROMA_PATH = "chroma"
COLLECTION = "fault_notes"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
EMBED_MODEL = "text-embedding-3-small"

TOP_K = 3
MAX_STEPS = 5
CRITICAL = {"BREAKER_FAIL"}
