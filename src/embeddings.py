"""Create semantic embeddings for JDs and candidate profiles.

Pipeline:
    Text (JD or candidate profile) -> Sentence Transformer -> embedding vector

The same model is used on both sides so their vectors can be compared with
cosine similarity in a later matching step.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol, Sequence

import numpy as np
from numpy.typing import NDArray


DEFAULT_MODEL = "all-MiniLM-L6-v2"


class SentenceTransformerModel(Protocol):
    """The Sentence Transformer interface used by this module."""

    def encode(
        self,
        sentences: str | Sequence[str],
        *,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> NDArray[np.float32]: ...


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = DEFAULT_MODEL) -> SentenceTransformerModel:
    """Load the embedding model once, only when an embedding is requested."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for embeddings. Install it with "
            "`pip install sentence-transformers`."
        ) from exc

    return SentenceTransformer(model_name)


def embed_text(
    text: str,
    *,
    model: SentenceTransformerModel | None = None,
) -> NDArray[np.float32]:
    """Embed one non-empty JD or candidate-profile text string."""
    if not text.strip():
        raise ValueError("Cannot create an embedding from empty text")

    encoder = model or get_embedding_model()
    return np.asarray(
        encoder.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ),
        dtype=np.float32,
    )


def embed_texts(
    texts: Sequence[str],
    *,
    model: SentenceTransformerModel | None = None,
) -> NDArray[np.float32]:
    """Embed a batch of non-empty JD or candidate-profile text strings."""
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    if any(not text.strip() for text in texts):
        raise ValueError("Cannot create embeddings from empty text")

    encoder = model or get_embedding_model()
    return np.asarray(
        encoder.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ),
        dtype=np.float32,
    )


def cosine_similarity(
    left_embedding: NDArray[np.floating],
    right_embedding: NDArray[np.floating],
) -> float:
    """Return cosine similarity for two same-sized embedding vectors.

    Embeddings produced by this module are already normalized, but calculating
    the norms here keeps the helper correct for externally supplied vectors.
    """
    left = np.asarray(left_embedding, dtype=np.float32).reshape(-1)
    right = np.asarray(right_embedding, dtype=np.float32).reshape(-1)
    if left.shape != right.shape:
        raise ValueError("Embeddings must have the same dimensions")

    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0:
        raise ValueError("Cosine similarity is undefined for a zero vector")
    return float(np.dot(left, right) / denominator)


def main() -> None:
    """Create an embedding for each clean JD as a quick manual check."""
    from src.data_loader import load_data
    from src.preprocessing import preprocess_job

    _, jobs = load_data()
    for _, job in jobs.iterrows():
        vector = embed_text(preprocess_job(job))
        print(f"{job.get('Name', 'Unnamed job')}: vector dimension={vector.size}")


if __name__ == "__main__":
    main()
