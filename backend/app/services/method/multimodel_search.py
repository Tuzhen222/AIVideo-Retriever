import numpy as np
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from app.services.method.clip_client import CLIPClient
from app.services.method.beit3_client import BEiT3Client
from app.services.method.bigg_client import BigGClient
from app.services.vector_db.qdrant_client import QdrantClient
from app.utils.scale import ScoreScaler
from app.utils.mapping import get_keyframe_path
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiModelSearch:

    def __init__(self):
        self.clip_weight = 0.25
        self.beit3_weight = 0.50
        self.bigg_weight = 0.25

        self.clip_client = CLIPClient()
        self.beit3_client = BEiT3Client()
        self.bigg_client = BigGClient()
        self.qdrant_client = QdrantClient()

        self.clip_collection = "clip"
        self.beit3_collection = "beit3"
        self.bigg_collection = "bigg_clip"

    def _extract_embeddings(self, query: str):
        def wrap(fn):
            try:
                emb = fn(query)
                return emb[0] if emb is not None and emb.size != 0 else None
            except:
                return None

        # Use more workers for concurrent embedding extraction
        with ThreadPoolExecutor(max_workers=6) as ex:
            clip_f = ex.submit(wrap, self.clip_client.extract_text_embedding)
            beit3_f = ex.submit(wrap, self.beit3_client.extract_text_embedding)
            bigg_f = ex.submit(wrap, self.bigg_client.extract_text_embedding)

        return clip_f.result(), beit3_f.result(), bigg_f.result()

    def _search(self, emb, col, top_k):
        if emb is None:
            return []
        try:
            return self.qdrant_client.search(col, emb, top_k)
        except:
            return []

    def search(self, query: str, top_k: Optional[int] = None):
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        clip_emb, beit3_emb, bigg_emb = self._extract_embeddings(query)

        # Use more workers for concurrent vector searches
        with ThreadPoolExecutor(max_workers=6) as ex:
            clip_f = ex.submit(self._search, clip_emb, self.clip_collection, top_k * 2)
            beit3_f = ex.submit(self._search, beit3_emb, self.beit3_collection, top_k * 2)
            bigg_f = ex.submit(self._search, bigg_emb, self.bigg_collection, top_k * 2)

        clip_res = clip_f.result()
        beit3_res = beit3_f.result()
        bigg_res = bigg_f.result()

        clip_z = ScoreScaler.z_score_normalize([r["score"] for r in clip_res])
        beit3_z = ScoreScaler.z_score_normalize([r["score"] for r in beit3_res])
        bigg_z = ScoreScaler.z_score_normalize([r["score"] for r in bigg_res])

        ensemble = defaultdict(float)
        meta = {}

        def accumulate(res, zlist, w):
            for r, z in zip(res, zlist):
                rid = r["id"]
                ensemble[rid] += z * w
                if rid not in meta:
                    meta[rid] = r.get("payload", {})

        accumulate(clip_res, clip_z, self.clip_weight)
        accumulate(beit3_res, beit3_z, self.beit3_weight)
        accumulate(bigg_res, bigg_z, self.bigg_weight)

        ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]

        final_scores = ScoreScaler.min_max_scale([s for _, s in ranked])

        results = []
        for (rid, _), s in zip(ranked, final_scores):
            results.append({
                "id": rid,
                "score": s,
                "payload": meta.get(rid, {}),
                "keyframe_path": get_keyframe_path(rid)
            })
        return results

    def search_single_model(self, query: str, model: str, top_k=None):
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        model = model.lower()
        try:
            if model == "clip":
                emb_result = self.clip_client.extract_text_embedding(query)
                if emb_result is None or emb_result.size == 0 or emb_result.shape[0] == 0:
                    logger.warning(f"[MULTIMODEL] CLIP returned empty embedding for query: {query}")
                    return []
                emb = emb_result[0]
                col = self.clip_collection
            elif model == "beit3":
                emb_result = self.beit3_client.extract_text_embedding(query)
                if emb_result is None or emb_result.size == 0 or emb_result.shape[0] == 0:
                    logger.warning(f"[MULTIMODEL] BEiT3 returned empty embedding for query: {query}")
                    return []
                emb = emb_result[0]
                col = self.beit3_collection
            elif model == "bigg":
                emb_result = self.bigg_client.extract_text_embedding(query)
                if emb_result is None or emb_result.size == 0 or emb_result.shape[0] == 0:
                    logger.warning(f"[MULTIMODEL] BIGG returned empty embedding for query: {query}")
                    return []
                emb = emb_result[0]
                col = self.bigg_collection
            else:
                return []
        except Exception as e:
            logger.error(f"[MULTIMODEL] Error extracting embedding for {model}: {e}")
            return []

        res = self.qdrant_client.search(col, emb, top_k)
        scaled = ScoreScaler.min_max_scale([r["score"] for r in res])

        out = []
        for r, s in zip(res, scaled):
            r["score"] = s
            r["keyframe_path"] = get_keyframe_path(r["id"])
            out.append(r)
        return out


_instance = None

def get_multimodel_search():
    global _instance
    if _instance is None:
        _instance = MultiModelSearch()
    return _instance
