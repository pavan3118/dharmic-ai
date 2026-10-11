import os
import chromadb
from typing import List, Dict, Any, Optional

class RetrieverService:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.chroma_path = os.path.join(base_dir, "data", "chroma_db")
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection("dharmic_sources")

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        tradition: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_filter = None
        if tradition:
            # Map canonical traditions flexibly
            t_clean = tradition.lower()
            if "gita" in t_clean:
                where_filter = {"$or": [{"tradition": "bhagavad_gita"}, {"tradition": "gita"}, {"tradition": "Bhagavad Gita"}]}
            elif "chanakya" in t_clean:
                where_filter = {"$or": [{"tradition": "chanakya_niti"}, {"tradition": "chanakya"}, {"tradition": "Chanakya Niti"}]}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter
            )
        except Exception:
            # Fallback without where filter if collection schema doesn't support $or or key mismatch
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

        # Fallback to search without filter if filtered search returns empty
        if not results or not results.get("documents") or not results["documents"][0]:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

        formatted_sources = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            ids = results["ids"][0] if "ids" in results else [f"doc_{i}" for i in range(len(docs))]
            metadatas = results["metadatas"][0] if ("metadatas" in results and results["metadatas"]) else [{}] * len(docs)

            for doc_id, doc_text, meta in zip(ids, docs, metadatas):
                formatted_sources.append({
                    "id": meta.get("canonical_id", doc_id),
                    "document": doc_text,
                    "metadata": meta
                })

        return formatted_sources

retriever_service = RetrieverService()