import os
import sqlite3

import chromadb
import pandas as pd
from chromadb.utils import embedding_functions

from . import config

ALIASES = {"OVERCURRENT_TRIP": "OC_TRIP", "TEMPERATURE_HIGH": "TEMP_HIGH"}


def load_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["device"] = df["device"].str.strip().str.upper()
    df["substation"] = df["substation"].str.strip().str.title()
    alarm = df["alarm"].str.strip().str.upper().str.replace(r"[\s\-]+", "_", regex=True)
    df["alarm"] = alarm.replace(ALIASES)
    df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d %H:%M")
    df[["current_a", "voltage_kv"]] = df[["current_a", "voltage_kv"]].apply(pd.to_numeric, errors="coerce")
    df["operator_note"] = df["operator_note"].fillna("").str.strip()
    df = df.drop_duplicates().sort_values("time").reset_index(drop=True)
    df.insert(0, "id", df.index + 1)
    return df


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    numbers = df[["id", "time", "device", "substation", "current_a", "voltage_kv", "alarm"]]
    notes = df.loc[df["operator_note"] != "", ["id", "device", "substation", "alarm", "operator_note"]]
    return numbers, notes.rename(columns={"operator_note": "text"})


def chunk(text: str, size: int = 200, overlap: int = 30) -> list[str]:
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]


def embedder():
    # OpenAI embeddings when a key is set, otherwise Chroma's local default model
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return embedding_functions.OpenAIEmbeddingFunction(api_key=key, model_name=config.EMBED_MODEL)
    return embedding_functions.DefaultEmbeddingFunction()


def build_sqlite(numbers: pd.DataFrame, path: str) -> None:
    conn = sqlite3.connect(path)
    numbers.to_sql("measurements", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_device_time ON measurements (device, time)")
    conn.commit()
    conn.close()


def build_index(notes: pd.DataFrame, path: str) -> int:
    client = chromadb.PersistentClient(path=path)
    try:
        client.delete_collection(config.COLLECTION)
    except Exception:
        pass
    col = client.create_collection(config.COLLECTION, embedding_function=embedder())
    ids, docs, metas = [], [], []
    for n in notes.itertuples(index=False):
        for k, part in enumerate(chunk(n.text)):
            ids.append(f"{n.id}-{k}")
            docs.append(part)
            metas.append({"note_id": int(n.id), "device": n.device, "substation": n.substation, "alarm": n.alarm})
    col.add(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def build_all(csv_path: str, db_path: str, chroma_path: str) -> tuple[int, int]:
    numbers, notes = split(load_clean(csv_path))
    build_sqlite(numbers, db_path)
    return len(numbers), build_index(notes, chroma_path)


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_collection(path: str):
    client = chromadb.PersistentClient(path=path)
    return client.get_collection(config.COLLECTION, embedding_function=embedder())
