import json
from datetime import date

from app.services.evolution import build_evolution, word_count

TODAY = date(2026, 10, 28)


def _series(**kwargs):
    base = dict(
        today=TODAY,
        days=14,
        messages=[],
        corrections=[],
        attempts=[],
        vocabulary=[],
        lessons=[],
        lesson_titles={},
    )
    base.update(kwargs)
    return build_evolution(**base)


def test_series_has_one_point_per_day_in_range():
    result = _series()
    assert len(result["series"]) == 14
    assert result["series"][-1]["day"] == "2026-10-28"
    assert result["series"][0]["day"] == "2026-10-15"


def test_word_count_ignores_extra_spaces():
    assert word_count("  I  would like   a coffee ") == 5


def test_accuracy_is_messages_without_correction_over_messages():
    result = _series(
        messages=[{"day": "2026-10-28", "content": "I goes home"}, {"day": "2026-10-28", "content": "I am fine"}],
        corrections=[{"day": "2026-10-28", "count": 1}],
    )
    today = result["series"][-1]
    assert today["user_messages"] == 2
    assert today["accuracy"] == 50.0


def test_days_without_activity_have_no_accuracy():
    result = _series()
    assert result["series"][-1]["accuracy"] is None
    assert result["series"][-1]["avg_words"] is None


def test_average_words_per_day():
    result = _series(messages=[
        {"day": "2026-10-28", "content": "Hi there"},
        {"day": "2026-10-28", "content": "I would like a coffee please"},
    ])
    assert result["series"][-1]["avg_words"] == 4.0


def test_cumulative_lessons_include_those_completed_before_the_window():
    result = _series(lessons=[
        {"lesson_id": "old", "score": 80, "completed_at": "2026-09-01T10:00:00+00:00"},
        {"lesson_id": "new", "score": 90, "completed_at": "2026-10-27T10:00:00+00:00"},
    ], lesson_titles={"new": "Nova lição"})
    assert result["series"][0]["cumulative_lessons"] == 1
    assert result["series"][-1]["cumulative_lessons"] == 2
    assert result["lesson_scores"][-1]["title"] == "Nova lição"


def test_exercise_accuracy_per_day():
    result = _series(attempts=[{"day": "2026-10-28", "correct": 3, "total": 4}])
    assert result["series"][-1]["exercise_accuracy"] == 75.0
    assert result["totals"]["exercise_accuracy"] == 75.0


def test_trend_compares_last_week_with_previous_week():
    msgs = []
    for offset in range(14):
        day = date.fromordinal(TODAY.toordinal() - offset).isoformat()
        words = "one two three" if offset < 7 else "one two"
        msgs.append({"day": day, "content": words})
    result = _series(days=14, messages=msgs)
    assert result["trend"]["avg_words"]["recent"] == 3.0
    assert result["trend"]["avg_words"]["previous"] == 2.0


def test_trend_is_none_without_enough_data():
    result = _series()
    assert result["trend"]["accuracy"] == {"recent": None, "previous": None}


def test_totals_empty_state_is_safe():
    totals = _series()["totals"]
    assert totals["user_messages"] == 0
    assert totals["conversation_accuracy"] is None
    assert totals["avg_words"] is None


# ----- endpoint ------------------------------------------------------------

def test_evolution_endpoint_returns_series_after_activity(client, fake_ollama):
    fake_ollama.replies.append(json.dumps({
        "reply": "Nice!",
        "correction": {"has_error": True, "original_text": "I goes", "corrected_text": "I go",
                       "explanation_pt": "", "error_category": "grammar", "severity": "minor",
                       "example_sentence": "", "practice_prompt": ""},
        "new_vocabulary": [],
    }))
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I goes to school every day"})

    body = client.get("/api/progress/evolution?days=30").json()
    assert body["range_days"] == 30
    assert len(body["series"]) == 30
    today = body["series"][-1]
    assert today["user_messages"] == 1
    assert today["corrections"] == 1
    assert today["accuracy"] == 0.0
    assert body["totals"]["user_messages"] == 1


def test_evolution_days_parameter_is_clamped(client):
    assert len(client.get("/api/progress/evolution?days=1").json()["series"]) == 7
    assert len(client.get("/api/progress/evolution?days=9999").json()["series"]) == 365
