import numpy as np


# A fixed k=3 gives the model a thin slice of context once a document
# has hundreds of chunks (e.g. a 300-page PDF) — the right answer is
# more likely to simply not be among the top 3 nearest chunks. Scaling
# k with corpus size (capped so context doesn't blow past the model's
# window) gives noticeably better recall on larger documents while
# leaving small documents untouched.
MIN_K = 3
MAX_K = 8


def _choose_k(num_chunks: int) -> int:
    """Pick how many chunks to retrieve based on how many exist.

    Small documents (few chunks) just get MIN_K, same as before. Larger
    documents get progressively more, capped at MAX_K so context stays
    bounded and retrieval/prompt-building time doesn't grow unchecked.
    """
    if num_chunks <= 0:
        return 0
    # Roughly one extra chunk of context per ~150 chunks in the corpus,
    # bounded to [MIN_K, MAX_K] — then capped to whatever actually
    # exists, so a 1-2 chunk document never asks for more than it has.
    scaled = MIN_K + (num_chunks // 150)
    k = max(MIN_K, min(MAX_K, scaled))
    return min(k, num_chunks)


def retrieve_chunks(question, model, vector_store, chunks, k=None):
    """Embed `question`, search `vector_store` for the nearest chunks,
    and return (context_string, retrieved_chunk_dicts).

    `k`, if not given, is chosen automatically based on how many chunks
    are in the document (see _choose_k). Pass an explicit k to override.

    Defensive: if there's no vector store or no chunks yet (e.g. called
    before a document finished loading), returns ("", []) instead of
    raising — callers already check `pdf_loaded` before this is called
    in normal operation, but this keeps the function safe to call on
    its own too.
    """
    if vector_store is None or not chunks:
        return "", []

    if k is None:
        k = _choose_k(len(chunks))
    else:
        k = max(0, min(k, len(chunks)))

    if k == 0:
        return "", []

    question_embedding = model.encode([question])

    distances, indices = vector_store.search(
        np.array(question_embedding).astype("float32"),
        k
    )

    retrieved_chunks = []
    context = ""

    for idx in indices[0]:
        # FAISS returns -1 for unfilled slots when k exceeds the index
        # size (shouldn't happen given the clamp above, but cheap to
        # guard against).
        if idx < 0 or idx >= len(chunks):
            continue

        chunk = chunks[idx]
        retrieved_chunks.append(chunk)
        context += chunk["text"] + "\n\n"

    return context, retrieved_chunks
