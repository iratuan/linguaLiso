import json

import pytest


def _correction_json(**overrides) -> str:
    correction = {
        "has_error": True,
        "original_text": "I goes to school",
        "corrected_text": "I go to school",
        "explanation_pt": "Com 'I' usamos o verbo sem -s.",
        "error_category": "grammar",
        "severity": "moderate",
        "example_sentence": "We go to school.",
        "practice_prompt": "Complete: She ___ to school.",
    }
    correction.update(overrides)
    return json.dumps(
        {"reply": "Good effort! Where do you study?", "correction": correction,
         "new_vocabulary": [{"term": "school", "translation_pt": "escola", "example_sentence": "I like school."}]}
    )


def test_health_and_diagnostics(client, fake_ollama):
    assert client.get("/api/health").json()["status"] == "ok"
    diag = client.get("/api/diagnostics").json()
    assert diag["llm"]["reachable"] is True
    assert diag["llm"]["model_installed"] is True
    assert diag["speech"]["stt_ready"] is True
    assert diag["backend"]["schema_version"] == 7


def test_profile_round_trip(client):
    assert client.get("/api/profile").json() is None
    saved = client.put("/api/profile", json={"display_name": "Ana", "level": "B1", "english_variant": "british",
                                              "explanation_language": "pt-BR", "study_minutes_goal": 30}).json()
    assert saved["level"] == "B1"
    assert client.get("/api/profile").json()["english_variant"] == "british"


def test_profile_rejects_invalid_level(client):
    response = client.put("/api/profile", json={"level": "Z1"})
    assert response.status_code == 422


def test_settings_update_and_validation(client):
    assert client.get("/api/settings").json()["llm_temperature"] == 0.7
    updated = client.put("/api/settings", json={"llm_temperature": 0.3, "history_limit": 6}).json()
    assert updated["llm_temperature"] == 0.3
    assert updated["history_limit"] == 6
    assert client.put("/api/settings", json={"llm_temperature": 9}).status_code == 422


def test_response_mode_defaults_to_audio_and_accepts_text(client):
    assert client.get("/api/settings").json()["response_mode"] == "audio"
    assert client.put("/api/settings", json={"response_mode": "text"}).json()["response_mode"] == "text"
    assert client.put("/api/settings", json={"response_mode": "video"}).status_code == 422


def test_free_conversation_persists_correction_and_vocabulary(client, fake_ollama):
    fake_ollama.replies.append(_correction_json())
    session = client.post("/api/sessions", json={"mode": "free"}).json()
    sid = session["id"]

    turn = client.post(f"/api/sessions/{sid}/messages",
                       json={"content": "I goes to school", "input_source": "voice"}).json()
    assert turn["structured"] is True
    assert turn["correction"]["corrected_text"] == "I go to school"
    assert turn["new_vocabulary"][0]["term"] == "school"

    transcript = client.get(f"/api/sessions/{sid}").json()
    roles = [m["role"] for m in transcript["messages"]]
    assert roles == ["user", "assistant"]
    assert transcript["messages"][0]["input_source"] == "voice"
    assert len(transcript["corrections"]) == 1

    vocab = client.get("/api/vocabulary").json()
    assert vocab["counts"]["total"] == 1


def test_history_is_sent_to_model_and_limited(client, fake_ollama):
    client.put("/api/settings", json={"history_limit": 2})
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    for i in range(4):
        client.post(f"/api/sessions/{sid}/messages", json={"content": f"message {i}"})
    # A requisição do turno real (a nova tentativa, se houver repetição, vem depois dela).
    last_request = next(
        r for r in reversed(fake_ollama.requests)
        if r["messages"][-1]["role"] == "user" and r["messages"][-1]["content"].startswith("message 3")
    )
    roles = [m["role"] for m in last_request["messages"]]
    assert roles[0] == "system"
    # history_limit=2 turnos => últimas 4 mensagens (user/assistant alternadas) + o novo user
    assert len(last_request["messages"]) - 1 <= 4
    assert last_request["messages"][-1]["content"].startswith("message 3")
    assert last_request["think"] is False
    assert last_request["format"]["required"] == ["reply", "correction", "new_vocabulary"]


def test_invalid_model_output_still_returns_reply(client, fake_ollama):
    fake_ollama.replies.append("Sure! Let's practice ordering food.")
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    turn = client.post(f"/api/sessions/{sid}/messages", json={"content": "hello"}).json()
    assert turn["structured"] is False
    assert turn["assistant_message"]["content"].startswith("Sure!")
    assert turn["correction"] is None


def test_ollama_offline_returns_503_and_keeps_user_message(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    fake_ollama.offline = True
    response = client.post(f"/api/sessions/{sid}/messages", json={"content": "hi there"})
    assert response.status_code == 503
    assert response.json()["code"] == "ollama_offline"
    transcript = client.get(f"/api/sessions/{sid}").json()
    assert [m["role"] for m in transcript["messages"]] == ["user"]


def test_missing_model_returns_actionable_message(client, fake_ollama):
    client.put("/api/settings", json={"llm_model": "qwen3:14b"})
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    response = client.post(f"/api/sessions/{sid}/messages", json={"content": "hi"})
    assert response.status_code == 503
    assert response.json()["code"] == "model_missing"
    assert "ollama pull qwen3:14b" in response.json()["detail"]


def test_status_reports_missing_model(client, fake_ollama):
    client.put("/api/settings", json={"llm_model": "qwen3:14b"})
    diag = client.get("/api/diagnostics").json()
    assert diag["llm"]["model_installed"] is False
    assert "ollama pull qwen3:14b" in diag["llm"]["message"]


def test_roleplay_requires_known_scenario(client):
    assert client.post("/api/sessions", json={"mode": "roleplay"}).status_code == 400
    assert client.post("/api/sessions", json={"mode": "roleplay", "scenario": "moon"}).status_code == 400
    ok = client.post("/api/sessions", json={"mode": "roleplay", "scenario": "airport"})
    assert ok.status_code == 201
    assert ok.json()["title"] == "Roleplay: airport"


def test_scenario_rejected_outside_roleplay(client):
    assert client.post("/api/sessions", json={"mode": "free", "scenario": "airport"}).status_code == 400


def test_ended_session_refuses_new_messages(client):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/end")
    response = client.post(f"/api/sessions/{sid}/messages", json={"content": "hello"})
    assert response.status_code == 409


def test_empty_and_oversized_messages_are_rejected(client):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/messages", json={"content": ""}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/messages", json={"content": "a" * 2001}).status_code == 422


def test_unknown_session_is_404(client):
    assert client.get("/api/sessions/999").status_code == 404
    assert client.post("/api/sessions/999/messages", json={"content": "hi"}).status_code == 404


def test_delete_session_cascades(client):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "hi"})
    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}").status_code == 404


def test_vocabulary_review_flow(client):
    item = client.post("/api/vocabulary", json={"term": "Bread", "translation_pt": "pão"}).json()
    assert item["box"] == 0
    reviewed = client.post(f"/api/vocabulary/{item['id']}/review", json={"rating": "good"}).json()
    assert reviewed["box"] == 1
    assert client.post("/api/vocabulary", json={"term": "bread"}).status_code == 400  # sem duplicar (NOCASE)
    assert client.post(f"/api/vocabulary/{item['id']}/review", json={"rating": "nope"}).status_code == 422
    assert client.post("/api/vocabulary/9999/review", json={"rating": "good"}).status_code == 404


def test_lesson_generation_answer_and_completion(client, fake_ollama):
    lesson_json = json.dumps({
        "title": "Present simple", "objective": "Usar o present simple",
        "content_md": "Use o verbo sem -s com I/you/we/they.",
        "exercises": [{"prompt": "Eu moro em São Paulo", "expected_answer": "I live in São Paulo"},
                      {"prompt": "Ela trabalha", "expected_answer": "She works"}],
    })
    fake_ollama.replies.append(lesson_json)
    lesson = client.post("/api/lessons", json={"objective": "present simple", "exercise_count": 2}).json()
    assert len(lesson["exercises"]) == 2
    lid = lesson["id"]

    fake_ollama.replies.append(json.dumps({"is_correct": True, "feedback_pt": "Muito bem!"}))
    after = client.post(f"/api/lessons/{lid}/answers", json={"position": 1, "answer": "I live in São Paulo"}).json()
    assert after["exercises"][0]["is_correct"] == 1

    assert client.post(f"/api/lessons/{lid}/answers", json={"position": 1, "answer": "x"}).status_code == 409

    done = client.post(f"/api/lessons/{lid}/complete").json()
    assert done["status"] == "completed"
    assert "Acertos: 1 de 2" in done["summary"]


def test_lesson_with_invalid_model_output_returns_502(client, fake_ollama):
    fake_ollama.replies.append("não é json")
    response = client.post("/api/lessons", json={"objective": "articles"})
    assert response.status_code == 502


def test_progress_and_recurring_errors(client, fake_ollama):
    fake_ollama.replies.append(_correction_json())
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I goes to school"})
    progress = client.get("/api/progress").json()
    assert progress["totals"]["corrections"] == 1
    assert progress["errors_by_category"][0]["category"] == "grammar"
    recurring = client.get("/api/errors/recurring").json()
    assert recurring[0]["corrected_text"] == "I go to school"


def test_error_review_mode_injects_recurring_errors(client, fake_ollama):
    fake_ollama.replies.append(_correction_json())
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I goes to school"})

    review = client.post("/api/sessions", json={"mode": "error_review"}).json()
    client.post(f"/api/sessions/{review['id']}/messages", json={"content": "ready"})
    system = fake_ollama.requests[-1]["messages"][0]["content"]
    assert "I go to school" in system


def test_export_and_delete_learner_data(client, fake_ollama):
    fake_ollama.replies.append(_correction_json())
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I goes to school"})
    client.put("/api/profile", json={"display_name": "Ana"})

    export = client.get("/api/data/export")
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    payload = export.json()
    assert payload["format"] == "english-teacher-local/1"
    assert len(payload["messages"]) == 2

    assert client.post("/api/data/delete", json={"confirm": "sim"}).status_code == 400
    assert client.post("/api/data/delete", json={"confirm": "APAGAR MEUS DADOS"}).json()["deleted"] is True
    assert client.get("/api/sessions").json() == []
    assert client.get("/api/profile").json() is None
    assert client.get("/api/settings").json()["llm_temperature"] == 0.7  # preferências preservadas


def test_speech_transcribe_and_synthesize(client, fake_speech):
    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("rec.webm", b"\x1a\x45\xdf\xa3fake", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "hello there"

    empty = client.post("/api/speech/transcribe", files={"audio": ("rec.webm", b"", "audio/webm")})
    assert empty.status_code == 400

    bad_type = client.post("/api/speech/transcribe", files={"audio": ("a.txt", b"x", "text/plain")})
    assert bad_type.status_code == 415

    audio = client.post("/api/speech/synthesize", json={"text": "Hello!"})
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"


def test_speech_offline_is_503_with_code(client_factory, fake_speech):
    import httpx

    client = client_factory()
    with client:
        def offline(request):
            raise httpx.ConnectError("refused", request=request)

        client.app.state.container.speech._transport = httpx.MockTransport(offline)
        response = client.post("/api/speech/transcribe", files={"audio": ("r.webm", b"abc", "audio/webm")})
        assert response.status_code == 503
        assert response.json()["code"] == "speech_offline"


def test_speech_audio_size_limit(client_factory):
    client = client_factory(max_audio_bytes=10)
    with client:
        response = client.post("/api/speech/transcribe", files={"audio": ("r.webm", b"x" * 50, "audio/webm")})
        assert response.status_code == 413


def test_deleting_a_conversation_removes_it_and_its_messages(client):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "hello there"})

    assert client.delete(f"/api/sessions/{sid}").status_code == 204
    assert client.get(f"/api/sessions/{sid}").status_code == 404
    assert all(s["id"] != sid for s in client.get("/api/sessions").json())
    assert client.delete(f"/api/sessions/{sid}").status_code == 404
