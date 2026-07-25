import pytest

from utils.llm import _parse_quiz_json


VALID_QUIZ = [
    {
        "question": "What is 2+2?",
        "options": ["1", "2", "3", "4"],
        "answer": "D",
        "explanation": "Basic arithmetic.",
    }
]


def test_parses_clean_json():
    import json
    result = _parse_quiz_json(json.dumps(VALID_QUIZ))
    assert result == VALID_QUIZ


def test_parses_json_wrapped_in_markdown_fence():
    import json
    fenced = f"```json\n{json.dumps(VALID_QUIZ)}\n```"
    result = _parse_quiz_json(fenced)
    assert result == VALID_QUIZ


def test_parses_json_wrapped_in_plain_fence():
    import json
    fenced = f"```\n{json.dumps(VALID_QUIZ)}\n```"
    result = _parse_quiz_json(fenced)
    assert result == VALID_QUIZ


def test_parses_json_with_stray_surrounding_text():
    import json
    text = f"Here is the quiz you asked for:\n\n{json.dumps(VALID_QUIZ)}\n\nHope that helps!"
    result = _parse_quiz_json(text)
    assert result == VALID_QUIZ


def test_raises_clear_error_on_genuinely_broken_output():
    with pytest.raises(ValueError):
        _parse_quiz_json("Sorry, I can't generate that right now.")
