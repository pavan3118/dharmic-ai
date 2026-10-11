import json
import os
import chromadb
from chromadb.config import Settings as ChromaSettings

SEED_DATA_PATH = "data/raw/seed_sources.json"
CHROMA_DIR = "data/chroma_db"

def ingest():
    if not os.path.exists(SEED_DATA_PATH):
        print(f"Error: {SEED_DATA_PATH} not found. Ensure the file is created.")
        return

    with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # Initialize local persistent Chroma client
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name="dharmic_sources")

    documents = []
    metadatas = []
    ids = []

    for item in sources:
        # Build dense text representation for semantic retrieval
        content = (
            f"Tradition: {item['tradition']}\n"
            f"Reference: Chapter {item['chapter']}, Verse/Sutra {item['verse_number']}\n"
            f"Sanskrit: {item['sanskrit_text']}\n"
            f"Translation: {item['english_translation']}\n"
            f"Core Meaning: {item.get('commentary_summary', '')}"
        )
        documents.append(content)
        metadatas.append({
            "canonical_id": item["canonical_id"],
            "tradition": item["tradition"],
            "chapter": item["chapter"],
            "verse_number": item["verse_number"],
            "sanskrit": item["sanskrit_text"],
            "translation": item["english_translation"]
        })
        ids.append(item["canonical_id"])

    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully ingested {len(ids)} verified records into ChromaDB at '{CHROMA_DIR}'")

if __name__ == "__main__":
    ingest()