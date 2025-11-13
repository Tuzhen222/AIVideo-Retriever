import logging
from typing import List
from elasticsearch import Elasticsearch
from app.core.config import settings

logger = logging.getLogger(__name__)


class ObjectFilterSearch:
    def __init__(self):
        self.host = settings.ELASTICSEARCH_HOST or "localhost"
        self.port = settings.ELASTICSEARCH_PORT or 9200

        es_url = f"http://{self.host}:{self.port}"

        config = {
            "hosts": [es_url],
            "request_timeout": settings.ELASTICSEARCH_REQUEST_TIMEOUT,
            "max_retries": settings.ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": settings.ELASTICSEARCH_RETRY_ON_TIMEOUT,
        }

        if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
            config["basic_auth"] = (
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD,
            )

        try:
            self.client = Elasticsearch(**config)
            self.client.info()
            logger.info("ObjectFilterSearch connected to Elasticsearch")
        except Exception as e:
            logger.error(f"ObjectFilterSearch init failed: {e}")
            raise

        self.index_name = "object"

    def filter(self, ids: List[str], selected_objects: List[str]) -> List[str]:

        if not selected_objects:
            logger.info("Object filter disabled → return original IDs")
            return ids

        selected_set = set(selected_objects)
        final_ids = []

        for rid in ids:
            try:
                doc = self.client.get(index=self.index_name, id=rid)
                obj_list = doc["_source"].get("objects", [])

                obj_set = set(obj_list)

                if selected_set.issubset(obj_set):
                    final_ids.append(rid)

            except Exception as e:
                logger.warning(f"[ObjectFilter] Failed to fetch ID {rid}: {e}")

        logger.info(
            f"[ObjectFilter] Before: {len(ids)} → After filter: {len(final_ids)} "
            f"(selected={selected_objects})"
        )

        return final_ids
