import numpy as np
import faiss

from utils.vector_store import create_vector_store, IVF_THRESHOLD


def _random_embeddings(n, dim=16, seed=0):
    rng = np.random.default_rng(seed)
    return rng.random((n, dim)).astype("float32")


def test_small_corpus_uses_flat_index():
    embeddings = _random_embeddings(50)
    index = create_vector_store(embeddings)

    assert isinstance(index, faiss.IndexFlatL2)
    assert index.ntotal == 50


def test_large_corpus_uses_ivf_index():
    embeddings = _random_embeddings(IVF_THRESHOLD + 500)
    index = create_vector_store(embeddings)

    assert isinstance(index, faiss.IndexIVFFlat)
    assert index.ntotal == IVF_THRESHOLD + 500


def test_search_returns_nearest_neighbor_correctly():
    embeddings = _random_embeddings(20)
    index = create_vector_store(embeddings)

    # Querying with a vector identical to one already in the index
    # should return that exact vector as the closest match.
    query = embeddings[5:6]
    distances, indices = index.search(query, 1)

    assert indices[0][0] == 5
    assert distances[0][0] == 0.0


def test_index_dimension_matches_input():
    embeddings = _random_embeddings(10, dim=32)
    index = create_vector_store(embeddings)

    assert index.d == 32
