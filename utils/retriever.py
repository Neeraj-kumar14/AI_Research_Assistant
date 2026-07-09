import numpy as np


def retrieve_chunks(question, model, vector_store, chunks, k=3):

    question_embedding = model.encode([question])

    distances, indices = vector_store.search(
        np.array(question_embedding).astype("float32"),
        k
    )

    retrieved_chunks = []

    context = ""

    for idx in indices[0]:

        chunk = chunks[idx]

        retrieved_chunks.append(chunk)

        context += chunk["text"] + "\n\n"

    return context, retrieved_chunks