import numpy as np

from utils.retriever import retrieve_chunks, _choose_k, MIN_K, MAX_K
from utils.vector_store import create_vector_store


class _FakeModel:
    """Stand-in for the sentence-transformers model: encode() returns a
    fixed embedding regardless of input text, matching whichever
    reference vector the test wired up as index[0]."""

    def __init__(self, dim=8):
        self.dim = dim

    def encode(self, texts):
        rng = np.random.default_rng(42)
        return rng.random((len(texts), self.dim)).astype("float32")


def _make_chunks(n):
    return [{"text": f"chunk {i}", "page": i, "source": "doc.pdf"} for i in range(n)]


def test_choose_k_stays_at_minimum_for_small_documents():
    assert _choose_k(10) == MIN_K


def test_choose_k_grows_for_larger_documents_but_is_capped():
    assert _choose_k(150) > MIN_K
    assert _choose_k(100_000) == MAX_K


def test_choose_k_never_exceeds_available_chunks():
    assert _choose_k(2) == 2


def test_retrieve_chunks_returns_empty_when_no_vector_store():
    context, sources = retrieve_chunks("question", _FakeModel(), None, _make_chunks(5))
    assert context == ""
    assert sources == []


def test_retrieve_chunks_returns_empty_when_no_chunks():
    fake_store = create_vector_store(np.random.default_rng(0).random((3, 8)).astype("float32"))
    context, sources = retrieve_chunks("question", _FakeModel(), fake_store, [])
    assert context == ""
    assert sources == []


def test_retrieve_chunks_returns_k_results_and_builds_context():
    model = _FakeModel(dim=8)
    embeddings = np.random.default_rng(1).random((20, 8)).astype("float32")
    store = create_vector_store(embeddings)
    chunks = _make_chunks(20)

    context, retrieved = retrieve_chunks("anything", model, store, chunks, k=4)

    assert len(retrieved) == 4
    for chunk in retrieved:
        assert chunk["text"] in context


def test_retrieve_chunks_clamps_k_to_available_chunks():
    model = _FakeModel(dim=8)
    embeddings = np.random.default_rng(2).random((3, 8)).astype("float32")
    store = create_vector_store(embeddings)
    chunks = _make_chunks(3)

    _, retrieved = retrieve_chunks("anything", model, store, chunks, k=50)

    assert len(retrieved) == 3
