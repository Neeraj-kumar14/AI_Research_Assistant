import faiss
import numpy as np

# Above this many vectors, switch from an exact flat index to an
# approximate IVF index. Flat is more accurate and is fine (and simpler)
# for typical documents; IVF trades a small amount of recall for much
# faster build/query time once you're indexing tens of thousands of
# chunks (large multi-file or 20-50MB+ uploads).
IVF_THRESHOLD = 5000


def create_vector_store(embeddings):
    embeddings = np.array(embeddings).astype("float32")
    n_vectors, dimension = embeddings.shape

    if n_vectors > IVF_THRESHOLD:
        nlist = max(1, min(int(n_vectors ** 0.5), 200))
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        index.train(embeddings)
        index.nprobe = min(10, nlist)
    else:
        index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)
    return index
