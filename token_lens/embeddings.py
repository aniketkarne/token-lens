"""Embedding backends used by the chunk-usefulness scorer."""
from __future__ import annotations

import hashlib
import math
import threading
from typing import Iterable, Protocol


_HASH_DIM = 64


def _char_trigrams(text: str) -> Iterable[str]:
    padded = f"  {text.lower()}  "
    for i in range(len(padded) - 2):
        yield padded[i : i + 3]


def hash_embed(text: str, dim: int = _HASH_DIM) -> list[float]:
    vec = [0.0] * dim
    for gram in _char_trigrams(text):
        digest = hashlib.md5(gram.encode("utf-8")).hexdigest()[:8]
        h_int = int(digest, 16)
        idx = h_int % dim
        sign = 1.0 if (h_int >> 31) & 1 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


class Embedder(Protocol):
    def encode(self, texts):
        ...


class HashEmbedder:
    def __init__(self, dim: int = _HASH_DIM):
        self.dim = dim

    def encode(self, texts):
        return [hash_embed(t, dim=self.dim) for t in texts]


class SentenceTransformerEmbedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model)

    def encode(self, texts):
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return [list(map(float, v)) for v in vectors]


_cache: dict = {}
_lock = threading.Lock()


def get_embedder(model: str = "all-MiniLM-L6-v2"):
    with _lock:
        if model in _cache:
            return _cache[model]
        try:
            emb = SentenceTransformerEmbedder(model)
        except Exception:
            emb = HashEmbedder()
        _cache[model] = emb
        return emb


__all__ = ["HashEmbedder", "SentenceTransformerEmbedder", "get_embedder", "hash_embed"]
