"""Tests for the embedding backend (hash + sentence-transformers fallback)."""
import pytest

from token_lens.embeddings import (
    HashEmbedder,
    get_embedder,
    hash_embed,
)


def test_hash_embed_deterministic():
    a = hash_embed("hello world")
    b = hash_embed("hello world")
    assert a == b


def test_hash_embed_returns_64d_vector():
    v = hash_embed("anything")
    assert isinstance(v, list)
    assert len(v) == 64
    assert all(isinstance(x, float) for x in v)


def test_hash_embed_different_inputs_give_different_vectors():
    a = hash_embed("the quick brown fox")
    b = hash_embed("completely unrelated topic about quantum physics")
    assert a != b


def test_hash_embed_similar_inputs_have_higher_similarity_than_unrelated():
    import math
    a = hash_embed("Paris is the capital of France.")
    b = hash_embed("What is the capital of France?")
    c = hash_embed("Pizza toppings are a matter of taste.")

    def cos(x, y):
        nx = math.sqrt(sum(t * t for t in x)) or 1.0
        ny = math.sqrt(sum(t * t for t in y)) or 1.0
        return sum(i * j for i, j in zip(x, y)) / (nx * ny)

    sim_ab = cos(a, b)
    sim_ac = cos(a, c)
    assert sim_ab > sim_ac


def test_get_embedder_returns_object_with_encode_method():
    e = get_embedder(model="all-MiniLM-L6-v2")
    out = e.encode(["hello", "world"])
    assert isinstance(out, list)
    assert len(out) == 2
    assert all(isinstance(v, list) for v in out)


def test_get_embedder_caches_by_model():
    e1 = get_embedder(model="all-MiniLM-L6-v2")
    e2 = get_embedder(model="all-MiniLM-L6-v2")
    assert e1 is e2


def test_hash_embedder_encode_returns_list_of_vectors():
    h = HashEmbedder(dim=64)
    out = h.encode(["a", "bb", "ccc"])
    assert len(out) == 3
    for v in out:
        assert len(v) == 64
