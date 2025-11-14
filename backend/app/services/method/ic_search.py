import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import cohere

from app.core.config import settings
from app.services.method.qwen_client import QwenClient
from app.services.vector_db.qdrant_client import QdrantClient
from app.utils.mapping import get_keyframe_path
from app.services.gemini.reset_api_key import APIKeyManager

logger = logging.getLogger(__name__)


class ICSearch:
    def __init__(self):
        self.qwen = QwenClient()
        self.qdrant = QdrantClient()
        self.collection = "IC"

        ic_path = Path("app/data/index/es_data/IC.json")
        if not ic_path.exists():
            raise FileNotFoundError(f"IC.json not found: {ic_path}")

        self.ic_data = json.loads(ic_path.read_text(encoding="utf-8"))
        logger.info(f"IC.json loaded: {len(self.ic_data)} entries")

        if not settings.COHERE_API_KEYS:
            raise ValueError("COHERE_API_KEYS must be set in ENV")

        self.key_manager = APIKeyManager(settings.COHERE_API_KEYS)

    def _client(self):
        key = self.key_manager.get_next_key()
        return cohere.Client(key)

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        top_k = top_k or settings.DEFAULT_TOP_K

        emb = self.qwen.extract_text_embedding(query)
        if emb.size == 0:
            logger.error("[IC] Qwen returned EMPTY embedding")
            return []

        q_results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=emb[0],
            top_k=top_k
        )

        if not q_results:
            logger.info("[IC] Qdrant returned 0 results")
            return []

        try:
            qdrant_debug = ", ".join(
                f"{r['id']}:{r['score']:.4f}" for r in q_results[:20]
            )
            logger.info(f"[IC] Qdrant top results (id:score): {qdrant_debug}")
        except Exception:
            pass

        doc_ids = []
        doc_texts = []

        empty_text_ids = []

        for r in q_results:
            rid = str(r["id"])
            text = self.ic_data.get(rid, "")

            # Log empty text
            if not text or text.strip() == "":
                empty_text_ids.append(rid)

            doc_ids.append(rid)
            doc_texts.append(text)

        if empty_text_ids:
            logger.warning(f"[IC] EMPTY TEXT FOUND for IDs: {empty_text_ids[:20]} (showing max 20)")

        co = self._client()

        rerank = co.rerank(
            model="rerank-multilingual-v3.0",   
            query=query,
            documents=doc_texts,
            top_n=top_k
        )

        try:
            cohere_debug = ", ".join(
                f"{doc_ids[item.index]}:{item.relevance_score:.4f}"
                for item in rerank.results[:20]
            )
            logger.info(f"[IC] Cohere rerank (id:score): {cohere_debug}")
        except Exception:
            pass

        final = []
        for item in rerank.results:
            idx = item.index
            rid = doc_ids[idx]

            final.append({
                "id": rid,
                "score": float(item.relevance_score),
                "text": doc_texts[idx],
                "method": "ic",
                "keyframe_path": get_keyframe_path(rid)
            })

        return final


_ic_instance = None

def get_ic_search():
    global _ic_instance
    if _ic_instance is None:
        _ic_instance = ICSearch()
    return _ic_instance
