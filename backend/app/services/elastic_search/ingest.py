"""
Elasticsearch ingestion script for JSON files in es_data folder
Uses bulk API to ingest all JSON files with index names based on file names (lowercase)
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tqdm import tqdm

from app.core.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchIngester:
    """Elasticsearch ingester for JSON files"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        index_prefix: str = None
    ):
        """Initialize Elasticsearch client"""
        self.host = host or settings.ELASTICSEARCH_HOST or "localhost"
        self.port = port or settings.ELASTICSEARCH_PORT or 9200
        self.index_prefix = index_prefix or settings.ELASTICSEARCH_INDEX_PREFIX or "es_data"
        
        # Build Elasticsearch connection URL
        es_url = f"http://{self.host}:{self.port}"
        
        # Prepare client configuration
        # Use compatibility headers for Elasticsearch 8.x server
        from elasticsearch import __versionstr__
        client_config = {
            "hosts": [es_url],
            "request_timeout": settings.ELASTICSEARCH_REQUEST_TIMEOUT,
            "max_retries": settings.ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": settings.ELASTICSEARCH_RETRY_ON_TIMEOUT,
            # Set headers to use ES 8.x compatibility
            "headers": {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        }
        
        # Add authentication if provided
        if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
            client_config["basic_auth"] = (
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD
            )
        
        # Add SSL configuration if enabled
        if settings.ELASTICSEARCH_USE_SSL:
            client_config["use_ssl"] = True
            client_config["verify_certs"] = settings.ELASTICSEARCH_VERIFY_CERTS
            # Use https URL
            es_url = f"https://{self.host}:{self.port}"
            client_config["hosts"] = [es_url]
        
        # Initialize Elasticsearch client
        self.client = Elasticsearch(**client_config)
        
        # Test connection - use info() instead of ping() for better compatibility
        try:
            info = self.client.info()
            logger.info(f"✅ Connected to Elasticsearch at {self.host}:{self.port}")
            logger.info(f"   Cluster: {info.get('cluster_name', 'unknown')}, Version: {info.get('version', {}).get('number', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Elasticsearch: {e}")
            logger.error(f"   Host: {self.host}, Port: {self.port}")
            raise
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded {file_path.name}: {len(data)} records")
            return data
        except Exception as e:
            logger.error(f"❌ Failed to load {file_path}: {e}")
            raise
    
    def create_index_mapping(self, index_name: str, data_sample: Dict[str, Any]) -> Dict[str, Any]:
        """Create index mapping based on data structure"""
        # Get first value to determine structure
        first_key = next(iter(data_sample.keys()))
        first_value = data_sample[first_key]
        
        # Determine field type
        if isinstance(first_value, str):
            # Text field for string values (IC, ASR, OCR)
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        }
                    }
                }
            }
        elif isinstance(first_value, list):
            # Keyword array for object lists (OBJECT)
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "objects": {
                            "type": "keyword"
                        }
                    }
                }
            }
        else:
            # Default mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "content": {
                            "type": "text"
                        }
                    }
                }
            }
        
        return mapping
    
    def prepare_documents(self, data: Dict[str, Any], index_name: str) -> List[Dict[str, Any]]:
        """Prepare documents for bulk ingestion"""
        documents = []
        
        for key, value in data.items():
            doc = {
                "_index": index_name,
                "_id": key,
            }
            
            if isinstance(value, str):
                # For IC, ASR, OCR - text content
                doc["_source"] = {
                    "id": key,
                    "content": value
                }
            elif isinstance(value, list):
                # For OBJECT - array of objects
                doc["_source"] = {
                    "id": key,
                    "objects": value
                }
            else:
                # Fallback
                doc["_source"] = {
                    "id": key,
                    "content": str(value)
                }
            
            documents.append(doc)
        
        return documents
    
    def ingest_file(self, file_path: Path, batch_size: int = 1000) -> None:
        """Ingest a single JSON file into Elasticsearch"""
        # Get index name from file name (lowercase, without extension)
        index_name = file_path.stem.lower()
        
        logger.info(f"📦 Starting ingestion for {file_path.name} -> index: {index_name}")
        
        # Load JSON data
        data = self.load_json_file(file_path)
        
        if not data:
            logger.warning(f"⚠️  No data in {file_path.name}, skipping")
            return
        
        # Check if index exists, create if not
        if not self.client.indices.exists(index=index_name):
            logger.info(f"📝 Creating index: {index_name}")
            mapping = self.create_index_mapping(index_name, data)
            # Elasticsearch 8.x Python client - use mappings parameter directly
            self.client.indices.create(
                index=index_name,
                mappings=mapping.get("mappings", {}),
                settings=mapping.get("settings", {}) if "settings" in mapping else None
            )
        else:
            logger.info(f"ℹ️  Index {index_name} already exists, will update documents")
        
        # Prepare documents
        documents = self.prepare_documents(data, index_name)
        
        # Bulk ingest with progress bar
        total_docs = len(documents)
        logger.info(f"🚀 Ingesting {total_docs} documents into {index_name}...")
        
        success_count = 0
        failed_count = 0
        
        # Process in batches
        for i in tqdm(range(0, total_docs, batch_size), desc=f"Ingesting {index_name}"):
            batch = documents[i:i + batch_size]
            
            try:
                success, failed_items = bulk(
                    self.client,
                    batch,
                    raise_on_error=False,
                    stats_only=False
                )
                
                success_count += success
                failed_count += len(failed_items) if failed_items else 0
                
                # Log failed items if any
                if failed_items:
                    for item in failed_items:
                        error_info = item.get('index', {})
                        logger.warning(f"⚠️  Failed to index document {error_info.get('_id')}: {error_info.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"❌ Error ingesting batch {i//batch_size + 1}: {e}")
                failed_count += len(batch)
        
        logger.info(f"✅ Completed {index_name}: {success_count} succeeded, {failed_count} failed")
    
    def ingest_all_files(self, data_dir: Path, batch_size: int = 1000) -> None:
        """Ingest all JSON files in the data directory"""
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        # Find all JSON files
        json_files = list(data_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"⚠️  No JSON files found in {data_dir}")
            return
        
        logger.info(f"📁 Found {len(json_files)} JSON files in {data_dir}")
        
        # Ingest each file
        for json_file in sorted(json_files):
            try:
                self.ingest_file(json_file, batch_size=batch_size)
            except Exception as e:
                logger.error(f"❌ Failed to ingest {json_file.name}: {e}")
                continue
        
        logger.info("🎉 All files ingested successfully!")


def main():
    """Main function to run ingestion"""
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get data directory path from settings or environment
    # Use INDEX_DIR from settings (e.g., "app/data/index" or "/app/app/data/index")
    index_dir = settings.INDEX_DIR
    if not index_dir.startswith('/'):
        # Relative path - resolve from app root
        base_path = Path(__file__).parent.parent.parent.parent
        data_dir = base_path / index_dir / "es_data"
    else:
        # Absolute path (e.g., in Docker: /app/app/data/index)
        data_dir = Path(index_dir) / "es_data"
    
    # Allow custom path via command line
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    
    if not data_dir.exists():
        logger.error(f"❌ Data directory not found: {data_dir}")
        logger.error(f"   INDEX_DIR setting: {settings.INDEX_DIR}")
        logger.error(f"   Tried path: {data_dir}")
        # Try alternative paths
        alt_paths = [
            Path("/app/app/data/index/es_data"),  # Docker path
            Path("/app/data/index/es_data"),      # Alternative Docker path
            base_path / "app" / "data" / "index" / "es_data",  # If base_path is /app
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                logger.info(f"✅ Found data directory at: {alt_path}")
                data_dir = alt_path
                break
        else:
            sys.exit(1)
    
    # Initialize ingester
    try:
        ingester = ElasticsearchIngester()
    except Exception as e:
        logger.error(f"❌ Failed to initialize Elasticsearch client: {e}")
        sys.exit(1)
    
    # Ingest all files
    try:
        ingester.ingest_all_files(data_dir, batch_size=20000)
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

