import json
import logging
import os
import sys

# IMPORTANT: torch must be imported before faiss to prevent OpenMP/BLAS runtime conflicts on macOS
import torch
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("rag.build_index")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATTACKS_FILE = os.path.join(BASE_DIR, "data", "attacks", "attacks.jsonl")
RAG_DATA_DIR = os.path.join(BASE_DIR, "data", "rag")
INDEX_PATH = os.path.join(RAG_DATA_DIR, "attack_index.faiss")
METADATA_PATH = os.path.join(RAG_DATA_DIR, "metadata.json")
MODEL_NAME = "all-MiniLM-L6-v2"

def build_index(
    attacks_file: str = ATTACKS_FILE,
    output_dir: str = RAG_DATA_DIR,
    model_name: str = MODEL_NAME
) -> tuple[int, int]:
    """
    Reads known attacks from JSONL, computes normalized embeddings with all-MiniLM-L6-v2,
    indexes with FAISS IndexFlatIP, and persists the index and metadata.
    Returns (num_records, embedding_dim).
    """
    os.makedirs(output_dir, exist_ok=True)
    index_file = os.path.join(output_dir, "attack_index.faiss")
    meta_file = os.path.join(output_dir, "metadata.json")

    if not os.path.exists(attacks_file):
        raise FileNotFoundError(f"Attacks corpus file not found: {attacks_file}")

    logger.info(f"Loading attacks from {attacks_file}...")
    corpus = []
    with open(attacks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                corpus.append(json.loads(line))

    if not corpus:
        raise ValueError(f"No records found in {attacks_file}")

    texts = [item["text"] for item in corpus]
    logger.info(f"Loaded {len(corpus)} attacks. Loading embedding model '{model_name}'...")
    model = SentenceTransformer(model_name)

    logger.info("Computing normalized embeddings for attack corpus...")
    # normalize_embeddings=True ensures vectors have unit L2 length (dot product = cosine similarity)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    logger.info(f"Creating FAISS IndexFlatIP with dimension {dim}...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    logger.info(f"Saving FAISS index to {index_file}...")
    faiss.write_index(index, index_file)

    logger.info(f"Saving metadata to {meta_file}...")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2)

    logger.info(f"Successfully built and persisted index with {len(corpus)} vectors.")
    return len(corpus), dim

def main():
    build_index()

if __name__ == "__main__":
    main()
