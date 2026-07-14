def create_chunks(pages, chunk_size=1800, overlap=150):
    """chunk_size/overlap tuned for large (3-5MB) documents: bigger chunks
    with a smaller overlap ratio means far fewer total chunks to embed,
    which is the single biggest lever on processing time for big files.
    (Old defaults of 1000/200 produced ~30-40% more chunks than this.)"""

    chunks = []

    for page in pages:

        text = page["text"]

        if not text or not text.strip():
            continue

        start = 0
        text_len = len(text)
        step = chunk_size - overlap

        while start < text_len:

            end = start + chunk_size
            piece = text[start:end].strip()

            if piece:
                chunks.append(
                    {
                        "text": piece,
                        "page": page["page"],
                        "source": page["source"]
                    }
                )

            start += step

    return chunks