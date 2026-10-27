import json
import logging
import os
import time
from typing import Any, Optional

# IMPORTANT: torch must be imported before faiss to prevent OpenMP/BLAS runtime conflicts on macOS
import torch
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

logger = logging.getLogger("gateway.rag")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAG_DATA_DIR = os.path.join(BASE_DIR, "data", "rag")
INDEX_PATH = os.path.join(RAG_DATA_DIR, "attack_index.faiss")
METADATA_PATH = os.path.join(RAG_DATA_DIR, "metadata.json")
MODEL_NAME = "all-MiniLM-L6-v2"


class AttackRetriever:
    """
    RAG-based Attack Retrieval Engine.
    Loads FAISS index and all-MiniLM-L6-v2 embedding model once at startup (singleton).
    Provides cosine-similarity matching against indexed adversarial attack prompts.
    """

    _instance: Optional["AttackRetriever"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        index_path: str = INDEX_PATH,
        metadata_path: str = METADATA_PATH,
        model_name: str = MODEL_NAME,
        lazy_load: bool = False,
    ):
        if getattr(self, "_initialized", False):
            return

        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.metadata: list[dict[str, Any]] = []
        self._is_ready = False

        if not lazy_load:
            self._load_resources()

        self._initialized = True

    def _load_resources(self):
        """Loads embedding model and FAISS index into memory once."""
        try:
            # 1. Load FAISS index and metadata
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                logger.info(
                    f"Loaded FAISS index ({self.index.ntotal} vectors) from {self.index_path}"
                )
            else:
                logger.warning(
                    f"FAISS index or metadata not found at {self.index_path}. Attempting build..."
                )
                from app.rag.build_index import build_index

                count, dim = build_index(output_dir=os.path.dirname(self.index_path))
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                logger.info(f"Built and loaded FAISS index ({count} vectors).")

            # 2. Load Embedding Model on CPU for fast sub-10ms inference
            logger.info(f"Loading embedding model '{self.model_name}' on CPU...")
            self.model = SentenceTransformer(self.model_name, device="cpu")
            self._is_ready = True
            logger.info("AttackRetriever ready for similarity searches.")
        except Exception as e:
            logger.error(f"Failed to initialize AttackRetriever: {e}")
            self._is_ready = False

    def is_available(self) -> bool:
        """Returns True if model and index are loaded and ready."""
        return self._is_ready and self.model is not None and self.index is not None

    def retrieve_similar_attacks(
        self, prompt: str, k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Retrieves top-k most similar known attack prompts for the given input prompt.
        Returns list of dicts: [{id, text, category, score}, ...]
        Scores represent cosine similarities in range [-1.0, 1.0].
        """
        if not prompt or not isinstance(prompt, str) or not self.is_available():
            return []

        k = max(1, min(k, len(self.metadata)))
        try:
            # Normalize embedding so inner product equals cosine similarity
            query_vec = self.model.encode(
                [prompt], normalize_embeddings=True, show_progress_bar=False
            )
            query_vec = np.ascontiguousarray(query_vec, dtype=np.float32)

            scores, indices = self.index.search(query_vec, k)
            results = []

            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                meta = self.metadata[idx]
                results.append(
                    {
                        "id": meta["id"],
                        "text": meta["text"],
                        "category": meta["category"],
                        "score": round(float(score), 4),
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error during attack retrieval: {e}")
            return []


# Module singleton instance loaded once at startup
_retriever = AttackRetriever()


def retrieve_similar_attacks(prompt: str, k: int = 5) -> list[dict[str, Any]]:
    """Public convenience function matching required specification."""
    return _retriever.retrieve_similar_attacks(prompt, k=k)


def get_retriever() -> AttackRetriever:
    """Returns singleton instance of AttackRetriever."""
    return _retriever
