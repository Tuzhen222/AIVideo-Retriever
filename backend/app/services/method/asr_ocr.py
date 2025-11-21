import logging
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from app.core.config import settings
from app.utils.mapping import get_keyframe_path, get_scene_keyframe_path

logger = logging.getLogger(__name__)


class ASROCRSearch:
    def __init__(self):
        self.host = settings.ELASTICSEARCH_HOST or "localhost"
        self.port = settings.ELASTICSEARCH_PORT or 9200

        es_url = f"http://{self.host}:{self.port}"
        config = {
            "hosts": [es_url],
            "request_timeout": settings.ELASTICSEARCH_REQUEST_TIMEOUT,
            "max_retries": settings.ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": settings.ELASTICSEARCH_RETRY_ON_TIMEOUT,
            "headers": {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        }

        if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
            config["basic_auth"] = (
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD
            )

        if settings.ELASTICSEARCH_USE_SSL:
            es_url = f"https://{self.host}:{self.port}"
            config["hosts"] = [es_url]
            config["use_ssl"] = True
            config["verify_certs"] = settings.ELASTICSEARCH_VERIFY_CERTS

        try:
            self.client = Elasticsearch(**config)
            self.client.info()
        except Exception as e:
            logger.error(f"Elasticsearch connection failed: {e}")
            raise

    def search(
        self,
        query: str,
        index_name: str,
        method_name: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:

        top_k = top_k or settings.DEFAULT_TOP_K

        try:
            body = {
                "query": {"match": {"content": {"query": query, "fuzziness": "AUTO"}}},
                "size": top_k
            }

            response = self.client.search(index=index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            results = []
            for hit in hits:
                rid = hit["_id"]
                path = (
                    get_keyframe_path(rid)
                    if method_name == "ocr"
                    else get_scene_keyframe_path(rid)
                )

                results.append({
                    "id": rid,
                    "score": float(hit["_score"]),
                    "content": hit["_source"].get("content", ""),
                    "method": method_name,
                    "keyframe_path": path
                })

            return results

        except Exception as e:
            logger.error(f"{method_name} search error: {e}")
            return []

    def search_asr(self, query: str, top_k: Optional[int] = None):
        return self.search(query, "asr", "asr", top_k)

    def search_ocr(self, query: str, top_k: Optional[int] = None):
        return self.search(query, "ocr", "ocr", top_k)


_instance: Optional[ASROCRSearch] = None

def get_asr_ocr_search() -> ASROCRSearch:
    global _instance
    if _instance is None:
        _instance = ASROCRSearch()
    return _instance
