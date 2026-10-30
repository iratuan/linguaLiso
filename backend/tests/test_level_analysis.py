"""Análise de nível: regras que o app aplica, verificações e endpoints."""

import json

from app.services.level_analysis import (
    ANALYSIS_SCHEMA,
    build_model_input,
    confidence_for,
    keep_verified_evidence,
    useful_student_turns,
)

MESSAGES = [
    {"id": 1, "role": "teacher", "text": "What is your job?"},
    {"id": 2, "role": "student", "text": "I worked as a software engineer for five years."},
    {"id": 3, "role": "student", "text": "Yes"},
]


def model_json(**overrides):
    base = {
        "level_estimate": "B1",
        "confidence": "alta",
        "level_reasoning_pt": "Frases com justificativa.",
        "level_vs_declared_pt": "Acima do declarado.",
        "criteria": {c: "B1" for c in ("vocabulary", "grammar", "fluency", "interaction", "coherence")},
        "strengths": [{"text_pt": "Experiência clara.", "evidence": {"message_id": 2, "quote": "I worked as a software engineer"}}],
        "improvement_points": [
            {"priority": "alta", "area": "grammar", "issue_pt": "Tempo verbal.",
             "evidence": {"message_id": 2, "quote": "for five years"},
             "suggestion_pt": "Pratique.", "better_example": "I have worked for five years.", "practice_pt": "Escreva 3 frases."},
            {"priority": "média", "area": "fluency", "issue_pt": "Inventado.",
             "evidence": {"message_id": 2, "quote": "I never said this"},
             "suggestion_pt": "x", "better_example": "y", "practice_pt": "z"},
        ],
        "transcription_doubts": [],
        "next_step_pt": "Praticar tempos verbais.",
    }
    base.update(overrides)
    return base


def test_confidence_follows_turn_and_doubt_counts():
    assert confidence_for(12, 0) == "alta"
    assert confidence_for(12, 3) == "média"
    assert confidence_for(7, 0) == "média"
    assert confidence_for(3, 0) == "baixa"
    assert confidence_for(12, 6) == "baixa"


def test_short_answers_do_not_count_as_useful_turns():
    cases = build_model_input(
        [{"id": 1, "role": "user", "content": "Yes"}, {"id": 2, "role": "user", "content": "I am from Brazil"}],
        mode="free", scenario=None, declared_level="A1",
    )
    assert useful_student_turns(cases["messages"]) == 1


def test_citations_that_do_not_exist_are_removed():
    result, removed = keep_verified_evidence(model_json(), MESSAGES)
    assert removed == 1
    assert [p["evidence"]["quote"] for p in result["improvement_points"]] == ["for five years"]
    assert len(result["strengths"]) == 1


def test_citation_from_teacher_message_is_not_accepted():
    bad = model_json(strengths=[{"text_pt": "x", "evidence": {"message_id": 1, "quote": "What is your job?"}}])
    result, _ = keep_verified_evidence(bad, MESSAGES)
    assert result["strengths"] == []


def test_schema_requires_the_fields_the_app_depends_on():
    assert {"level_estimate", "criteria", "improvement_points", "transcription_doubts"} <= set(ANALYSIS_SCHEMA["required"])


def test_analysis_endpoint_stores_a_verified_result(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I worked as a software engineer for five years."})
    # Usa o id real da fala do aluno (o modelo recebe os ids reais das mensagens).
    student_id = next(m["id"] for m in client.get(f"/api/sessions/{sid}").json()["messages"] if m["role"] == "user")
    reply = model_json(confidence="alta")
    reply["strengths"][0]["evidence"]["message_id"] = student_id
    reply["improvement_points"][0]["evidence"]["message_id"] = student_id
    reply["improvement_points"][1]["evidence"]["message_id"] = student_id
    fake_ollama.replies.append(json.dumps(reply))

    response = client.post(f"/api/sessions/{sid}/analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["level_estimate"] == "B1"
    assert body["confidence"] == "baixa"  # só 1 fala útil: o app corrige a confiança do modelo
    assert body["removed_citations"] == 1  # a citação "I never said this" não existe na fala
    assert len(body["improvement_points"]) == 1

    listed = client.get("/api/analyses").json()["analyses"]
    assert listed[0]["session_id"] == sid and listed[0]["level_estimate"] == "B1"
    assert client.get(f"/api/analyses/{body['id']}").json()["criteria"]["vocabulary"] == "B1"


def test_analysis_refuses_conversation_without_student_turns(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    response = client.post(f"/api/sessions/{sid}/analysis")
    assert response.status_code == 400


def test_analysis_is_removed_with_its_session(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I like to read books every single day."})
    fake_ollama.replies.append(json.dumps(model_json()))
    client.post(f"/api/sessions/{sid}/analysis")
    client.delete(f"/api/sessions/{sid}")
    assert client.get("/api/analyses").json()["analyses"] == []
