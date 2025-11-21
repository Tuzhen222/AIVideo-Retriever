"""
Ingest .bin files into Qdrant collections
Creates collections with names matching .bin filenames and uploads vectors in batches
Optimized for fast ingestion using large batch sizes and efficient numpy operations
"""
import os
import numpy as np
from pathlib import Path
from typing import Optional
import logging
from tqdm import tqdm
import time
import faiss

from app.core.config import settings
from app.services.vector_db.qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)


def load_bin_file(bin_path: Path) -> np.ndarray:
    """Load .bin file as numpy array"""
    try:
        # Try loading as numpy array
        data = np.fromfile(bin_path, dtype=np.float32)
        return data
    except Exception as e:
        logger.error(f"❌ Failed to load {bin_path}: {e}")
        raise


def load_faiss_index(bin_path: Path):
    """Load faiss index from .bin file"""
    try:
        index = faiss.read_index(str(bin_path))
        return index
    except Exception as e:
        logger.error(f"❌ Failed to load faiss index from {bin_path}: {e}")
        raise


def get_vector_shape(data: np.ndarray, vector_size: int) -> tuple:
    """Determine vector shape from data and vector size"""
    total_elements = len(data)
    if vector_size == 0:
        raise ValueError("Vector size cannot be zero")
    
    num_vectors = total_elements // vector_size
    if total_elements % vector_size != 0:
        raise ValueError(f"Cannot divide {total_elements} elements into vectors of size {vector_size}")
    
    return (num_vectors, vector_size)


def ingest_collection(
    qdrant_client: QdrantClient,
    collection_name: str,
    bin_path: Path,
    vector_size: int,
    batch_size: int = 100,
    distance: Distance = Distance.COSINE
) -> None:
    """
    Ingest a single .bin file (faiss index) into Qdrant collection
    
    Args:
        qdrant_client: Qdrant client instance
        collection_name: Name of the collection (matches .bin filename)
        bin_path: Path to .bin file (faiss IndexFlatIP)
        vector_size: Size of each vector (dimensions)
        batch_size: Batch size for uploading vectors
        distance: Distance metric for collection (default: COSINE)
    """
    logger.info(f"🚀 Starting ingestion for {collection_name}...")
    start_time = time.time()
    
    # Load faiss index
    logger.info(f"📂 Loading faiss index from {bin_path}...")
    index = load_faiss_index(bin_path)
    
    # Get vector info from index
    num_vectors = index.ntotal
    detected_vector_size = index.d
    
    # Use detected size if vector_size not provided
    if vector_size != detected_vector_size:
        logger.info(f"📊 Using vector size from faiss index: {detected_vector_size} (was {vector_size})")
        vector_size = detected_vector_size
    
    logger.info(f"📊 Vector info: {num_vectors} vectors × {vector_size} dimensions")
    
    # Reconstruct all vectors from faiss index
    logger.info(f"🔄 Reconstructing vectors from faiss index...")
    vectors = index.reconstruct_n(0, num_vectors)  # Reconstruct all vectors
    vectors = np.array(vectors).astype(np.float32)
    
    # Check if collection exists, create if not
    try:
        collections = qdrant_client.client.get_collections()
        collection_exists = collection_name in [col.name for col in collections.collections]
    except Exception:
        collection_exists = False
    
    if collection_exists:
        logger.warning(f"⚠️  Collection {collection_name} already exists, skipping creation")
    else:
        logger.info(f"📦 Creating collection: {collection_name} (distance={distance})")
        qdrant_client.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance
            )
        )
    
    # Prepare IDs (simple sequential: 0, 1, 2, ...)
    ids = list(range(num_vectors))
    
    # Upload vectors in batches (optimized for speed)
    logger.info(f"🚀 Uploading {num_vectors} vectors in batches of {batch_size}...")
    
    total_batches = (num_vectors + batch_size - 1) // batch_size
    
    # Use larger batch size for better performance (Qdrant gRPC handles large batches well)
    # Process in chunks to avoid memory issues while maximizing throughput
    with tqdm(total=num_vectors, desc=f"Uploading {collection_name}", unit="vectors") as pbar:
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, num_vectors)
            
            # Use numpy views for efficiency (no copy)
            batch_vectors = vectors[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]
            
            # Convert numpy array to list if needed
            if isinstance(batch_vectors, np.ndarray):
                batch_vectors = batch_vectors.tolist()
            
            # Create points
            points = []
            for vector, point_id in zip(batch_vectors, batch_ids):
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=None
                ))
            
            # Upload batch (gRPC handles this efficiently)
            qdrant_client.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            pbar.update(len(batch_vectors))
    
    elapsed_time = time.time() - start_time
    logger.info(f"✅ Completed {collection_name}: {num_vectors} vectors in {elapsed_time:.2f}s ({num_vectors/elapsed_time:.1f} vectors/s)")


def main():
    """Main ingestion function"""
    # Setup paths
    bin_dir = Path(settings.INDEX_DIR) / "bin"
    
    if not bin_dir.exists():
        raise FileNotFoundError(f"Bin directory not found: {bin_dir}")
    
    # Find all .bin files
    bin_files = list(bin_dir.glob("*.bin"))
    if not bin_files:
        raise FileNotFoundError(f"No .bin files found in {bin_dir}")
    
    logger.info(f"📁 Found {len(bin_files)} .bin files:")
    for bin_file in bin_files:
        logger.info(f"  - {bin_file.name}")
    
    # Initialize Qdrant client with retry
    logger.info("🔌 Connecting to Qdrant...")
    max_retries = settings.QDRANT_RETRY_ATTEMPTS
    retry_delay = settings.QDRANT_RETRY_DELAY
    qdrant_client = None
    
    for attempt in range(max_retries):
        try:
            qdrant_client = QdrantClient()
            logger.info("✅ Connected to Qdrant")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️  Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                logger.info(f"   Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"❌ Failed to connect to Qdrant after {max_retries} attempts")
                raise
    
    if qdrant_client is None:
        raise RuntimeError("Failed to initialize Qdrant client")
    
    # Get batch size from settings
    batch_size = settings.QDRANT_BATCH_SIZE
    logger.info(f"⚙️  Using batch size: {batch_size} (increase for faster upload)")
    
    # Get vector size from settings or use default
    # You may need to configure this per collection or detect from first file
    vector_size = settings.VECTOR_SIZE
    
    # Ingest each .bin file
    total_start_time = time.time()
    
    for bin_file in bin_files:
        # Collection name = filename without extension
        collection_name = bin_file.stem
        
        # Detect vector size from faiss index
        current_vector_size = vector_size
        if current_vector_size is None:
            # Load faiss index to get vector size
            try:
                index = load_faiss_index(bin_file)
                current_vector_size = index.d
                num_vectors = index.ntotal
                logger.info(f"✅ Detected via faiss: vector_size={current_vector_size}, num_vectors={num_vectors} for {collection_name}")
            except Exception as e:
                logger.warning(f"⚠️  Could not read as faiss index, trying fallback method: {e}")
                # Fallback: Load file and try common vector sizes
                data = load_bin_file(bin_file)
                total_elements = len(data)
                
                # Try common vector sizes
                for common_size in [768, 1024, 1536, 2048, 384, 512, 256, 128, 4096, 5120, 6400]:
                    if total_elements % common_size == 0:
                        num_vectors = total_elements // common_size
                        if num_vectors > 0 and num_vectors < 10000000:
                            current_vector_size = common_size
                            logger.info(f"🔍 Detected vector size: {current_vector_size} for {collection_name} ({num_vectors} vectors)")
                            break
                
                if current_vector_size is None:
                    raise ValueError(f"Cannot determine vector size for {collection_name}. File has {total_elements} elements. Please set VECTOR_SIZE in settings.")
        
        try:
            ingest_collection(
                qdrant_client=qdrant_client,
                collection_name=collection_name,
                bin_path=bin_file,
                vector_size=current_vector_size,
                batch_size=batch_size,
                distance=Distance.COSINE
            )
        except Exception as e:
            logger.error(f"❌ Failed to ingest {collection_name}: {e}")
            raise
    
    total_elapsed = time.time() - total_start_time
    logger.info(f"🎉 All collections ingested in {total_elapsed:.2f}s")
    logger.info(f"📊 Collections created: {[f.stem for f in bin_files]}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    main()

