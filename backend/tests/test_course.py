import json
from pathlib import Path

import pytest

from app.curriculum.loader import Curriculum, CurriculumError, normalize, shuffled_words


@pytest.fixture
def course(client):
    return client.app.state.container.curriculum.get("en")


def _lesson_exercises(client, lesson_id):
    return client.get(f"/api/course/lessons/{lesson_id}").json()["exercises"]


def _answer_key(course, exercise_id):
    """Resposta correta de cada tipo, usada para completar lições nos testes."""
    ex = course.exercise(exercise_id)
    if ex.type == "multiple_choice":
        return ex.data["answer"]
    if ex.type == "listen":
        return ex.data["text"]
    return ex.answers[0]


def _complete_lesson(client, course, lesson_id, *, correct: bool):
    for ex in _lesson_exercises(client, lesson_id):
        answer = _answer_key(course, ex["id"])
        if not correct and ex["type"] == "multiple_choice":
            answer = (answer + 1) % len(ex["options"])
        elif not correct:
            answer = "definitely wrong answer"
        client.post(f"/api/course/exercises/{ex['id']}/check", json={"answer": answer})
    return client.post(f"/api/course/lessons/{lesson_id}/complete")


# ----- currículo -----------------------------------------------------------

def test_curriculum_has_five_levels_and_is_sequential(course):
    assert [lv.code for lv in course.levels] == ["A1", "A2", "B1", "B2", "C1"]
    assert len(course.lessons) == 90
    assert [lesson.index for lesson in course.lessons] == list(range(90))
    assert course.exercise_count == 360


def test_conversation_lessons_are_part_of_each_level(course):
    for level in course.levels:
        conversation = [u for u in level.units if u.id.endswith("-cu1") or u.id.endswith("-cu2")]
        assert len(conversation) == 2, level.code


def test_open_reply_exercises_have_context_and_examples(course):
    for lesson in course.lessons:
        for ex in lesson.exercises:
            if ex.type == "open_reply":
                assert ex.data.get("context"), ex.id
                assert len(ex.answers) >= 2, ex.id


def test_every_lesson_has_at_least_three_exercises(course):
    assert all(len(lesson.exercises) >= 3 for lesson in course.lessons)


def test_reorder_words_form_the_answer(course):
    for lesson in course.lessons:
        for ex in lesson.exercises:
            if ex.type == "reorder":
                assert sorted(normalize(" ".join(ex.data["words"])).split()) == sorted(
                    normalize(ex.answers[0]).split()
                ), ex.id


def test_validator_rejects_malformed_exercise(tmp_path):
    bad = {
        "level": "A1", "title": "x", "description": "x", "goal": "x",
        "units": [{"id": "u", "title": "u", "goal": "g", "lessons": [{
            "id": "bad", "title": "t", "objective": "o", "explanation": "e",
            "exercises": [
                {"id": "bad-1", "type": "multiple_choice", "prompt": "p", "options": ["a"], "answer": 0},
                {"id": "bad-2", "type": "fill_blank", "prompt": "p", "answers": ["x"]},
                {"id": "bad-3", "type": "fill_blank", "prompt": "p", "answers": ["x"]},
            ],
        }]}],
    }
    (tmp_path / "a1.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(CurriculumError, match="pelo menos 2 opções"):
        Curriculum.load(tmp_path)


def test_validator_rejects_duplicate_ids(tmp_path):
    lesson = {"id": "dup", "title": "t", "objective": "o", "explanation": "e", "exercises": [
        {"id": f"e{i}", "type": "fill_blank", "prompt": "p", "answers": ["x"]} for i in range(3)]}
    level = {"level": "A1", "title": "x", "description": "x", "goal": "x",
             "units": [{"id": "u", "title": "u", "goal": "g", "lessons": [lesson, lesson]}]}
    (tmp_path / "a1.json").write_text(json.dumps(level), encoding="utf-8")
    with pytest.raises(CurriculumError, match="duplicada"):
        Curriculum.load(tmp_path)


# ----- normalização e embaralhamento --------------------------------------

@pytest.mark.parametrize("a, b", [
    ("My name is Carlos.", "my name is carlos"),
    ("It’s fine!", "it's fine"),
    ("Café", "cafe"),
    ("  I   am  ", "i am"),
])
def test_normalize_matches_equivalent_answers(a, b):
    assert normalize(a) == normalize(b)


def test_normalize_keeps_apostrophes_distinct():
    assert normalize("it's") != normalize("its")


def test_shuffled_words_is_stable_and_a_permutation(course):
    ex = next(e for lesson in course.lessons for e in lesson.exercises if e.type == "reorder")
    first = shuffled_words(ex)
    assert first == shuffled_words(ex)
    assert sorted(first) == sorted(ex.data["words"])


# ----- visão geral e bloqueio ----------------------------------------------

def test_overview_starts_at_first_lesson_and_locks_the_rest(client):
    overview = client.get("/api/course").json()
    assert overview["next_lesson_id"] == "a1-1-1"
    assert overview["progress"] == {"completed": 0, "total": 90, "percent": 0}
    lessons = [l for lv in overview["levels"] for u in lv["units"] for l in u["lessons"]]
    assert lessons[0]["status"] == "available"
    assert all(l["locked"] for l in lessons[1:])


def test_locked_lesson_is_forbidden(client):
    response = client.get("/api/course/lessons/a1-2-1")
    assert response.status_code == 403
    assert response.json()["code"] == "locked"


def test_lesson_payload_hides_answers(client):
    lesson = client.get("/api/course/lessons/a1-1-1").json()
    text = json.dumps(lesson)
    assert '"answers"' not in text
    assert '"answer":' not in text
    mc = next(e for e in lesson["exercises"] if e["type"] == "multiple_choice")
    assert "answer" not in mc
    assert mc["options"]


def test_listen_exercise_does_not_expose_the_text(client, course):
    _complete_lesson(client, course, "a1-1-1", correct=True)
    lesson = client.get("/api/course/lessons/a1-1-2").json()
    listen = next(e for e in lesson["exercises"] if e["type"] == "listen")
    assert listen["has_audio"] is True
    assert "text" not in listen


# ----- correção -----------------------------------------------------------

def test_multiple_choice_correct_and_wrong(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    right = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": ex.data["answer"]}).json()
    assert right["correct"] is True
    assert right["feedback_pt"] == ex.explanation
    assert right["correct_answer"] is None

    wrong_index = (ex.data["answer"] + 1) % len(ex.data["options"])
    wrong = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": wrong_index}).json()
    assert wrong["correct"] is False
    assert wrong["correct_answer"] == ex.data["options"][ex.data["answer"]]


def test_fill_blank_accepts_normalized_variants(client, course):
    ex = course.lesson("a1-1-1").exercises[1]  # "She ___ from Brazil." -> is
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": " IS "}).json()
    assert result["correct"] is True


def test_translate_exact_match_does_not_call_ai(client, course, fake_ollama):
    ex = course.lesson("a1-1-1").exercises[2]  # "Eu sou estudante."
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": "I'm a student"}).json()
    assert result["correct"] is True
    assert result["used_ai_check"] is False
    assert fake_ollama.requests == []


def test_translate_variant_is_judged_by_ai(client, course, fake_ollama):
    ex = course.lesson("a1-1-1").exercises[2]
    fake_ollama.replies.append(json.dumps({"is_correct": True, "feedback_pt": "Perfeito, sinônimo válido."}))
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": "I am a student, yes"}).json()
    assert result["correct"] is True
    assert result["used_ai_check"] is True
    assert result["feedback_pt"] == "Perfeito, sinônimo válido."


def test_translate_falls_back_to_literal_when_ai_offline(client, course, fake_ollama):
    ex = course.lesson("a1-1-1").exercises[2]
    fake_ollama.offline = True
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": "Totally different"}).json()
    assert result["correct"] is False
    assert result["used_ai_check"] is False
    assert result["correct_answer"] == "I am a student."


def test_check_rejects_empty_text_and_bad_index(client, course):
    ex_text = course.lesson("a1-1-1").exercises[1]
    ex_mc = course.lesson("a1-1-1").exercises[0]
    assert client.post(f"/api/course/exercises/{ex_text.id}/check", json={"answer": "   "}).status_code == 400
    assert client.post(f"/api/course/exercises/{ex_mc.id}/check", json={"answer": 99}).status_code == 400
    assert client.post("/api/course/exercises/nope/check", json={"answer": "x"}).status_code == 404


def test_checking_is_blocked_for_locked_lessons(client, course):
    ex = course.lesson("a1-2-1").exercises[0]
    response = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": 0})
    assert response.status_code == 403


# ----- conclusão e progressão ---------------------------------------------

def test_complete_requires_all_exercises_answered(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": ex.data["answer"]})
    response = client.post("/api/course/lessons/a1-1-1/complete")
    assert response.status_code == 400
    assert "faltam 3" in response.json()["detail"]


def test_passing_lesson_unlocks_the_next_one(client, course):
    result = _complete_lesson(client, course, "a1-1-1", correct=True)
    body = result.json()
    assert body["score"] == 100
    assert body["passed"] is True
    assert body["next_lesson_id"] == "a1-1-2"

    overview = client.get("/api/course").json()
    assert overview["next_lesson_id"] == "a1-1-2"
    assert overview["progress"]["completed"] == 1
    assert client.get("/api/course/lessons/a1-1-2").status_code == 200


def test_failing_lesson_keeps_next_lesson_locked(client, course):
    body = _complete_lesson(client, course, "a1-1-1", correct=False).json()
    assert body["score"] == 0
    assert body["passed"] is False
    assert body["next_lesson_id"] == "a1-1-1"
    assert client.get("/api/course/lessons/a1-1-2").status_code == 403


def test_pass_threshold_is_seventy_percent(client, course):
    lesson = course.lesson("a1-1-1")  # 4 exercícios: 3 acertos = 75%, 2 acertos = 50%
    for i, ex in enumerate(lesson.exercises):
        answer = _answer_key(course, ex.id) if i < 3 else "definitely wrong"
        client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": answer})
    body = client.post("/api/course/lessons/a1-1-1/complete").json()
    assert body["score"] == 75
    assert body["passed"] is True


def test_completed_lesson_can_be_redone_and_keeps_the_best_score(client, course):
    _complete_lesson(client, course, "a1-1-1", correct=True)  # 100%
    assert client.get("/api/course/lessons/a1-1-1").json()["status"] == "completed"

    # Refazer uma lição concluída: as respostas são limpas e podem ser dadas de novo.
    lesson = client.post("/api/course/lessons/a1-1-1/retry").json()
    assert all(not e["answered"] for e in lesson["exercises"])
    assert lesson["status"] == "completed"

    # Uma tentativa pior não reduz a nota já conquistada.
    _complete_lesson(client, course, "a1-1-1", correct=False)
    overview = client.get("/api/course").json()
    lesson_summary = next(l for lv in overview["levels"] for u in lv["units"] for l in u["lessons"] if l["id"] == "a1-1-1")
    assert lesson_summary["status"] == "completed"
    assert lesson_summary["score"] == 100

    # A próxima lição continua liberada durante todo o processo.
    assert client.get("/api/course/lessons/a1-1-2").status_code == 200


def test_retry_clears_answers_of_an_unfinished_lesson(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": 0})
    lesson = client.post("/api/course/lessons/a1-1-1/retry").json()
    assert all(not e["answered"] for e in lesson["exercises"])


def test_lesson_status_progresses_from_available_to_in_progress(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": ex.data["answer"]})
    overview = client.get("/api/course").json()
    lesson = next(l for lv in overview["levels"] for u in lv["units"] for l in u["lessons"] if l["id"] == "a1-1-1")
    assert lesson["status"] == "in_progress"


# ----- áudio de escuta ----------------------------------------------------

def test_listening_exercise_returns_audio(client, course):
    listen_id = next(e.id for e in course.lesson("a1-1-2").exercises if e.type == "listen")
    # a1-1-2 está bloqueada: é preciso concluir a anterior antes.
    _complete_lesson(client, course, "a1-1-1", correct=True)
    response = client.get(f"/api/course/exercises/{listen_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"


def test_audio_is_refused_for_non_listening_exercises(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    assert client.get(f"/api/course/exercises/{ex.id}/audio").status_code == 404


def test_export_includes_course_progress(client, course):
    _complete_lesson(client, course, "a1-1-1", correct=True)
    payload = client.get("/api/data/export").json()
    assert any(row["lesson_id"] == "a1-1-1" for row in payload["course_lesson_progress"])


# ----- respostas livres de conversa ---------------------------------------

def _unlock_open_reply(client, course):
    """Conclui as lições anteriores e devolve o primeiro exercício de resposta livre da lição de conversa."""
    target = course.lesson("a1-c1-1")
    for lesson in course.lessons[: target.index]:
        _complete_lesson(client, course, lesson.id, correct=True)
    return next(e for e in target.exercises if e.type == "open_reply")


def test_open_reply_exact_example_is_accepted_without_ai(client, course, fake_ollama):
    ex = _unlock_open_reply(client, course)
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": ex.answers[0]}).json()
    assert result["correct"] is True
    assert result["used_ai_check"] is False
    assert fake_ollama.requests == []


def test_open_reply_paraphrase_is_judged_by_ai(client, course, fake_ollama):
    ex = _unlock_open_reply(client, course)
    fake_ollama.replies.append(json.dumps({"is_correct": True, "feedback_pt": "Resposta natural e adequada."}))
    result = client.post(
        f"/api/course/exercises/{ex.id}/check", json={"answer": "Hi Carlos, pleased to meet you. I'm Ana."}
    ).json()
    assert result["correct"] is True
    assert result["used_ai_check"] is True
    assert result["feedback_pt"] == "Resposta natural e adequada."
    # O prompt de conversa inclui a situação e os exemplos aceitos.
    prompt = fake_ollama.requests[-1]["messages"][0]["content"]
    assert "Você acabou de conhecer alguém" in prompt
    assert ex.answers[0] in prompt


def test_open_reply_without_ai_reports_the_example_answer(client, course, fake_ollama):
    ex = _unlock_open_reply(client, course)
    fake_ollama.offline = True
    result = client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": "Blah blah"}).json()
    assert result["correct"] is False
    assert result["correct_answer"] == ex.answers[0]


def test_every_attempt_is_recorded_in_history(client, course):
    ex = course.lesson("a1-1-1").exercises[0]
    client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": 0})
    client.post(f"/api/course/exercises/{ex.id}/check", json={"answer": 1})
    history = client.get("/api/data/export").json()["course_attempts"]
    mine = [row for row in history if row["exercise_id"] == ex.id]
    assert len(mine) == 2
    assert [row["correct"] for row in mine] == [1, 0]
