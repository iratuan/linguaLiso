from datetime import datetime, timedelta, timezone

import pytest

from app.domain import SRS_INTERVALS_DAYS
from app.services.srs import MAX_BOX, next_box, schedule_review
from app.services.teacher_response import parse_json_object, parse_teacher_output, teacher_json_schema

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


# ----- revisão espaçada ----------------------------------------------------

@pytest.mark.parametrize(
    "box, rating, expected",
    [
        (0, "good", 1),
        (3, "good", 4),
        (MAX_BOX, "good", MAX_BOX),
        (4, "forgot", 0),
        (5, "forgot", 0),
        (0, "hard", 1),
        (3, "hard", 3),
    ],
)
def test_next_box(box, rating, expected):
    assert next_box(box, rating) == expected


def test_schedule_uses_interval_of_new_box():
    box, due = schedule_review(0, "good", NOW)
    assert box == 1
    assert due == NOW + timedelta(days=SRS_INTERVALS_DAYS[1])


def test_forgot_is_due_tomorrow():
    box, due = schedule_review(5, "forgot", NOW)
    assert box == 0
    assert due == NOW + timedelta(days=1)


def test_invalid_box_and_rating_raise():
    with pytest.raises(ValueError):
        next_box(9, "good")
    with pytest.raises(ValueError):
        next_box(0, "meh")  # type: ignore[arg-type]


# ----- saída do modelo -----------------------------------------------------

VALID = """{
  "reply": "Nice try! Do you like pizza?",
  "correction": {"has_error": true, "original_text": "I goes home",
    "corrected_text": "I go home", "explanation_pt": "Com 'I', use o verbo sem -s.",
    "error_category": "grammar", "severity": "moderate",
    "example_sentence": "I go home at six.", "practice_prompt": "Complete: She ___ home."},
  "new_vocabulary": [{"term": "home", "translation_pt": "casa", "example_sentence": "I go home."}]
}"""


def test_parses_valid_structured_output():
    turn = parse_teacher_output(VALID)
    assert turn.structured is True
    assert turn.correction is not None and turn.correction.corrected_text == "I go home"
    assert turn.new_vocabulary[0].term == "home"


def test_parses_json_inside_code_fence_and_surrounding_text():
    raw = "Aqui está:\n```json\n" + VALID + "\n```\nObrigado!"
    turn = parse_teacher_output(raw)
    assert turn.structured is True
    assert turn.reply.startswith("Nice try")


def test_strips_thinking_block():
    turn = parse_teacher_output("<think>hmm</think>" + VALID)
    assert turn.structured is True


def test_no_error_means_no_correction():
    raw = '{"reply": "Great!", "correction": {"has_error": false, "original_text": "", "corrected_text": "",' \
          ' "explanation_pt": "", "error_category": "other", "severity": "minor", "example_sentence": "",' \
          ' "practice_prompt": ""}, "new_vocabulary": []}'
    turn = parse_teacher_output(raw)
    assert turn.correction is None


def test_invalid_json_falls_back_to_plain_text():
    turn = parse_teacher_output("Sure, let's talk about your weekend!")
    assert turn.structured is False
    assert turn.correction is None
    assert "weekend" in turn.reply


def test_empty_output_gets_safe_message():
    turn = parse_teacher_output("   ")
    assert turn.structured is False
    assert turn.reply


def test_bad_enum_value_falls_back_without_crashing():
    raw = VALID.replace('"grammar"', '"banana"')
    turn = parse_teacher_output(raw)
    assert turn.structured is False


def test_vocabulary_without_term_is_dropped():
    raw = '{"reply": "Hi", "correction": null, "new_vocabulary": [{"term": " ", "translation_pt": "x"}]}'
    turn = parse_teacher_output(raw)
    assert turn.new_vocabulary == []


def test_parse_json_object_returns_none_for_non_object():
    assert parse_json_object("[1, 2]") is None
    assert parse_json_object("nada") is None


def test_schema_requires_all_fields_used_by_parser():
    schema = teacher_json_schema()
    assert set(schema["required"]) == {"reply", "correction", "new_vocabulary"}
    assert set(schema["properties"]["correction"]["required"]) >= {"has_error", "corrected_text"}
