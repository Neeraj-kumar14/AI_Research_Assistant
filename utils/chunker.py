def create_chunks(pages, chunk_size=1000, overlap=200):

    chunks = []

    for page in pages:

        text = page["text"]

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunks.append(
                {
                    "text": text[start:end],
                    "page": page["page"],
                    "source": page["source"]
                }
            )

            start += chunk_size - overlap

    return chunks