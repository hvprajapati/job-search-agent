"""Local embedding service using all-MiniLM-L6-v2 via sentence-transformers.

Replaces the non-functional DeepSeek embedding API with a fast, local model.
384-dimensional embeddings. ~80MB model. ~10ms per text on CPU.
"""

from __future__ import annotations
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384
_model = None
_model_lock = threading.Lock()


def _load_model():
    """Lazy-load the sentence-transformers model. Thread-safe."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {MODEL_NAME}")
            _model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Model loaded. Dimension: {_model.get_sentence_embedding_dimension()}")
        except ImportError:
            logger.error(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def get_embedding_dim() -> int:
    """Get the vector dimension of the loaded model."""
    return VECTOR_DIM


def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding vector. Returns Python list of floats."""
    if not text or not text.strip():
        return [0.0] * VECTOR_DIM
    try:
        model = _load_model()
        # Truncate long texts to avoid memory issues
        truncated = text[:8000]
        embedding: "np.ndarray" = model.encode(truncated, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Embedding generation failed, returning zero vector: {e}")
        return [0.0] * VECTOR_DIM


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts. Batch processing for efficiency."""
    if not texts:
        return []
    try:
        model = _load_model()
        truncated = [t[:8000] if t else " " for t in texts]
        embeddings: "np.ndarray" = model.encode(truncated, normalize_embeddings=True)
        return embeddings.tolist()
    except Exception as e:
        logger.warning(f"Batch embedding failed: {e}")
        return [[0.0] * VECTOR_DIM for _ in texts]


def is_available() -> bool:
    """Check if the embedding model can be loaded."""
    try:
        _load_model()
        return True
    except Exception:
        return False
