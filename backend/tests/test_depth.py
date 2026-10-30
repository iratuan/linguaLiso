"""Profundidade progressiva: a orientação do professor avança com as falas do aluno."""

from app.services.depth import DEEPENING_MODES, depth_guidance, depth_stage


def test_stage_advances_with_user_turns():
    assert [depth_stage(n) for n in (1, 2, 3, 5, 6, 9, 10, 40)] == [1, 1, 2, 2, 3, 3, 4, 4]


def test_guidance_names_the_stage_and_asks_one_deepening_question():
    text = depth_guidance(7, "B1")
    assert "estágio 3 de 4" in text
    assert "UMA pergunta" in text
    assert "frases curtas" not in text


def test_beginner_levels_keep_simple_words():
    assert "frases curtas" in depth_guidance(4, "A1")
    assert "frases curtas" in depth_guidance(4, "A2")


def test_only_open_conversation_modes_deepen():
    assert {"free", "grammar", "vocabulary"} == DEEPENING_MODES
    assert "roleplay" not in DEEPENING_MODES
    assert "guided_lesson" not in DEEPENING_MODES


def test_guidance_reaches_the_model_and_grows_with_the_conversation(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    for i in range(6):
        client.post(f"/api/sessions/{sid}/messages", json={"content": f"I like tea number {i}."})

    system_prompts = [req["messages"][0]["content"] for req in fake_ollama.requests]
    assert "estágio 1 de 4" in system_prompts[0]
    assert "aluno com 1 falas" in system_prompts[0]
    assert "estágio 3 de 4" in system_prompts[-1]
    assert "aluno com 6 falas" in system_prompts[-1]


def test_roleplay_does_not_get_the_deepening_block(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "roleplay", "scenario": "airport"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "Hello"})
    assert "PROFUNDIDADE DA CONVERSA" not in fake_ollama.requests[-1]["messages"][0]["content"]
