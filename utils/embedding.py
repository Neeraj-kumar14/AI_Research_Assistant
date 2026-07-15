import os
import time
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

from utils.concurrency import cpu_job


@st.cache_resource
def load_embedding_model():
    # MiniLM instead of the larger mpnet model: at 20-50MB document scale
    # (potentially tens of thousands of chunks), embedding speed matters
    # more than the small accuracy gap between the two — MiniLM is
    # roughly 4-5x faster to encode with on CPU and still covers the
    # same languages. Override via EMBEDDING_MODEL env var if you want
    # the more accurate model back for smaller-document use.
    import os
    model_name = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    model = SentenceTransformer(model_name)

    # Use all available CPU cores for encoding instead of the torch
    # default (often just 1-4 threads), which meaningfully speeds up
    # embedding on larger chunk sets when there's no GPU.
    try:
        import torch
        cpu_count = os.cpu_count() or 4
        torch.set_num_threads(min(6, max(1, cpu_count - 2)))
    except Exception:
        pass

    return model


# Load model only once
model = load_embedding_model()


def create_embeddings(chunks, batch_size=256, progress_callback=None):
    """Encode chunks in batches.

    batch_size=128 (up from the sentence-transformers default of 32) gives
    noticeably better CPU throughput on large chunk sets.

    progress_callback(done, total), if given, is called after each batch so
    the UI can show real progress instead of a single opaque spinner for
    what can be a 10-60s call on big documents.
    """
    if not chunks:
        return np.empty((0, model.get_sentence_embedding_dimension()), dtype="float32")

    if progress_callback is None:
        # Gate against other concurrent users' embedding/OCR jobs — see
        # utils/concurrency.py.
        with cpu_job():
            return model.encode(chunks, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)

    total = len(chunks)
    all_embeddings = []

    # for start in range(0, total, batch_size):
    #     batch = chunks[start:start + batch_size]
    #     batch_embeddings = model.encode(
    #         batch, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True
    #     )
    #     all_embeddings.append(batch_embeddings)
    #     progress_callback(min(start + batch_size, total), total)

    for start in range(0, total, batch_size):

        batch = chunks[start:start + batch_size]

        batch_start = time.perf_counter()

        # Gated per-batch (rather than for the whole document) so a
        # large upload doesn't monopolize a CPU slot end-to-end —
        # other users' batches/OCR jobs can interleave between ours.
        with cpu_job():
            batch_embeddings = model.encode(
                batch,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

        print(
            f"Batch {start // batch_size + 1}: "
            f"{len(batch)} chunks -> "
            f"{time.perf_counter() - batch_start:.2f} sec"
        )

        all_embeddings.append(batch_embeddings)

        progress_callback(min(start + batch_size, total), total)

    return np.vstack(all_embeddings)