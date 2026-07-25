from unittest.mock import patch, MagicMock

from utils import llm


class _FakeChunk:
    def __init__(self, text):
        self.choices = [MagicMock(delta=MagicMock(content=text))]


def test_stream_yields_tokens_from_first_working_candidate():
    def fake_create(*args, **kwargs):
        return iter([_FakeChunk("Hello "), _FakeChunk("world")])

    with patch.object(llm, "_get_fallback_chain", return_value=[("k1", "m1")]):
        with patch("utils.llm.Groq") as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = fake_create
            result = "".join(llm.chat_completion_stream([{"role": "user", "content": "hi"}]))

    assert result == "Hello world"


def test_stream_falls_back_to_next_candidate_on_initial_rate_limit():
    """A 429 on the *initial* request (before any streaming starts) should
    be caught and the next (key, model) candidate tried — mirroring
    chat_completion()'s non-streaming fallback behavior."""
    calls = {"n": 0}

    def fake_create(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise Exception("429 rate_limit_exceeded")
        return iter([_FakeChunk("Hello "), _FakeChunk("world")])

    with patch.object(llm, "_get_fallback_chain", return_value=[("k1", "m1"), ("k2", "m2")]):
        with patch("utils.llm.Groq") as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = fake_create
            result = "".join(llm.chat_completion_stream([{"role": "user", "content": "hi"}]))

    assert result == "Hello world"
    assert calls["n"] == 2


def test_stream_raises_immediately_on_non_rate_limit_error():
    def fake_create(*args, **kwargs):
        raise Exception("invalid_api_key")

    with patch.object(llm, "_get_fallback_chain", return_value=[("k1", "m1"), ("k2", "m2")]):
        with patch("utils.llm.Groq") as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = fake_create
            try:
                llm.chat_completion_stream([{"role": "user", "content": "hi"}])
                assert False, "expected an exception"
            except Exception as e:
                assert "invalid_api_key" in str(e)


def test_stream_raises_after_exhausting_all_candidates():
    def fake_create(*args, **kwargs):
        raise Exception("429 rate_limit_exceeded")

    with patch.object(llm, "_get_fallback_chain", return_value=[("k1", "m1"), ("k2", "m2")]):
        with patch("utils.llm.Groq") as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = fake_create
            try:
                llm.chat_completion_stream([{"role": "user", "content": "hi"}])
                assert False, "expected a RuntimeError"
            except RuntimeError as e:
                assert "rate-limited" in str(e)
