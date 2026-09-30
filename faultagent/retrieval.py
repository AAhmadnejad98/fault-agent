import re

from . import config

DEVICE = re.compile(r"\b([A-Z]{1,2}\d{1,3})\b", re.I)
SUBSTATION = re.compile(r"\b(north|south|east|west)\b", re.I)


def search_notes(collection, question: str, k: int = config.TOP_K) -> list[dict]:
    where = None
    if m := DEVICE.search(question):
        where = {"device": m.group(1).upper()}
    elif m := SUBSTATION.search(question):
        where = {"substation": m.group(1).title()}

    res = collection.query(query_texts=[question], n_results=k, where=where)
    notes, seen = [], set()
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if meta["note_id"] in seen:
            continue
        seen.add(meta["note_id"])
        notes.append({**meta, "text": doc, "distance": round(dist, 4)})
    return notes
