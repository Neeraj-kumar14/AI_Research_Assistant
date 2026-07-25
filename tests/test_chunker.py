from utils.chunker import create_chunks


def _page(text, page=1, source="doc.pdf"):
    return {"text": text, "page": page, "source": source}


def test_short_text_produces_single_chunk():
    pages = [_page("hello world", page=1)]
    chunks = create_chunks(pages, chunk_size=1800, overlap=150)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["page"] == 1
    assert chunks[0]["source"] == "doc.pdf"


def test_long_text_is_split_into_multiple_chunks():
    text = "a" * 5000
    pages = [_page(text)]
    chunks = create_chunks(pages, chunk_size=1800, overlap=150)

    assert len(chunks) > 1
    # step = chunk_size - overlap = 1650, so with a 5000-char input the
    # first two windows are full-size (1800) before the tail shrinks.
    assert len(chunks[0]["text"]) == 1800
    assert len(chunks[1]["text"]) == 1800
    # No chunk should ever exceed the configured chunk_size.
    assert all(len(c["text"]) <= 1800 for c in chunks)
    # Reassembling should cover the whole original text.
    assert chunks[-1]["text"] == text[-len(chunks[-1]["text"]):]


def test_chunks_overlap_by_the_configured_amount():
    text = "0123456789" * 300  # 3000 chars, easy to reason about
    chunk_size, overlap = 1000, 100
    pages = [_page(text)]
    chunks = create_chunks(pages, chunk_size=chunk_size, overlap=overlap)

    # The tail of chunk[i] should reappear at the head of chunk[i+1],
    # for exactly `overlap` characters.
    for i in range(len(chunks) - 1):
        end_of_first = chunks[i]["text"][-overlap:]
        start_of_second = chunks[i + 1]["text"][:overlap]
        assert end_of_first == start_of_second


def test_blank_and_whitespace_only_pages_are_skipped():
    pages = [
        _page("", page=1),
        _page("   \n\t  ", page=2),
        _page("real content here", page=3),
    ]
    chunks = create_chunks(pages)

    assert len(chunks) == 1
    assert chunks[0]["page"] == 3


def test_each_chunk_keeps_its_originating_page_and_source():
    pages = [
        _page("first page text", page=1, source="a.pdf"),
        _page("second page text", page=2, source="a.pdf"),
    ]
    chunks = create_chunks(pages, chunk_size=1800, overlap=150)

    assert [c["page"] for c in chunks] == [1, 2]
    assert all(c["source"] == "a.pdf" for c in chunks)


def test_empty_page_list_produces_no_chunks():
    assert create_chunks([]) == []
