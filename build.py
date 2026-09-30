from faultagent import config
from faultagent.data import build_all

if __name__ == "__main__":
    rows, chunks = build_all(config.CSV_PATH, config.DB_PATH, config.CHROMA_PATH)
    print(f"SQLite: {rows} rows -> {config.DB_PATH}")
    print(f"ChromaDB: {chunks} chunks -> {config.CHROMA_PATH}/")
