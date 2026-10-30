"""Personalidades do professor: escolha nas configurações, gravação na conversa e tom no prompt."""

import pytest

from app.domain import DEFAULT_PERSONA, TEACHER_PERSONAS
from app.services.prompt_library import PromptLibrary


def test_three_personas_exist_with_prompts_and_a_default(config):
    assert TEACHER_PERSONAS == ("formal", "descontraido", "nativo")
    assert DEFAULT_PERSONA == "descontraido"
    library = PromptLibrary(config.prompts_dir)
    for persona in TEACHER_PERSONAS:
        assert library.persona_prompt(persona)


def test_default_setting_is_the_relaxed_teacher(client):
    assert client.get("/api/settings").json()["teacher_persona"] == "descontraido"


def test_new_conversation_records_the_persona_chosen_in_settings(client):
    client.put("/api/settings", json={"teacher_persona": "nativo"})
    session = client.post("/api/sessions", json={"mode": "free"}).json()
    assert session["persona"] == "nativo"


def test_persona_tone_reaches_the_model(client, fake_ollama):
    client.put("/api/settings", json={"teacher_persona": "formal"})
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "Hello, I like tea."})
    system = fake_ollama.requests[-1]["messages"][0]["content"]
    assert "PERSONALIDADE: professor formal." in system


def test_each_conversation_keeps_its_own_persona_after_settings_change(client):
    client.put("/api/settings", json={"teacher_persona": "formal"})
    old = client.post("/api/sessions", json={"mode": "free"}).json()
    client.put("/api/settings", json={"teacher_persona": "nativo"})
    assert client.get(f"/api/sessions/{old['id']}").json()["session"]["persona"] == "formal"


def test_unknown_persona_is_rejected(client):
    response = client.put("/api/settings", json={"teacher_persona": "pirata"})
    assert response.status_code == 422


def test_ui_transparency_defaults_and_accepts_only_0_to_80(client):
    assert client.get("/api/settings").json()["ui_transparency"] == 45
    assert client.put("/api/settings", json={"ui_transparency": 60}).json()["ui_transparency"] == 60
    assert client.put("/api/settings", json={"ui_transparency": 90}).status_code == 422


def test_app_theme_defaults_to_dark_and_accepts_paper(client):
    assert client.get("/api/settings").json()["app_theme"] == "escuro"
    assert client.put("/api/settings", json={"app_theme": "papel"}).json()["app_theme"] == "papel"
    assert client.put("/api/settings", json={"app_theme": "sepia"}).status_code == 422
