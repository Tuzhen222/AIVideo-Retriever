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

        if not ids:
            return ids

        try:
            # Use Elasticsearch query to filter server-side (much more scalable)
            # This is faster than mget() + client-side filtering for large datasets
            query = {
                "bool": {
                    "filter": [
                        {"ids": {"values": ids}},  # Only search within result IDs
                        *[{"term": {"objects": obj}} for obj in selected_objects]  # All objects must exist
                    ]
                }
            }

            response = self.client.search(
                index=self.index_name,
                query=query,
                _source=False,  # Don't fetch document content, just IDs
                size=len(ids)   # Max results = input size
            )

            # Extract IDs from search hits
            final_ids = [hit["_id"] for hit in response["hits"]["hits"]]
            
            logger.info(f"Object filter: {len(ids)} → {len(final_ids)} results")
            return final_ids

        except Exception as e:
            logger.error(f"[ObjectFilter] Search query failed: {e}")
            # Fallback to original IDs if error
            return ids

        logger.info(
            f"[ObjectFilter] Before: {len(ids)} → After filter: {len(final_ids)} "
            f"(selected={selected_objects})"
        )

        return final_ids
