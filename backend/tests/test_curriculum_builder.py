"""Criação de lições pelo usuário: rascunhos, validação e aprovação."""

import json

from app.curriculum.loader import CurriculumError


def lesson_payload(title="Pedindo comida"):
    return {
        "title": title,
        "objective": "Pedir comida num restaurante.",
        "explanation": "Use **Can I have...** para pedir algo com educação.",
        "key_phrases": [{"en": "Can I see the menu?", "pt": "Posso ver o cardápio?"}],
        "exercises": [
            {"type": "multiple_choice", "prompt": "___ I have the bill?", "options": ["Can", "Is", "Do"],
             "answer": 0, "explanation": "Use *Can* para pedir."},
            {"type": "fill_blank", "prompt": "I ___ like a coffee.", "answers": ["would"],
             "explanation": "*would like* é educado."},
            {"type": "translate", "prompt": "Posso ver o cardápio?", "answers": ["Can I see the menu?"],
             "explanation": "Frase pronta."},
            {"type": "reorder", "prompt": "Monte: pode trazer a conta", "words": ["bill", "the", "bring", "you", "Can"],
             "answers": ["Can you bring the bill?"], "explanation": "Ordem de *Can you...*"},
            {"type": "listen", "prompt": "Ouça e digite.", "text": "I would like a coffee.",
             "answers": ["I would like a coffee."], "explanation": "Atenção ao *would*."},
        ],
    }


def generate(client, fake_ollama, reply, *, level="A1", count=1):
    fake_ollama.replies.append(reply if isinstance(reply, str) else json.dumps(reply))
    return client.post("/api/course/drafts", json={"level": level, "topic": "restaurante", "count": count})


def test_generated_lesson_is_a_draft_and_does_not_enter_the_trilha(client, fake_ollama):
    before = client.get("/api/course").json()
    response = generate(client, fake_ollama, lesson_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["failed"] == 0 and len(body["drafts"]) == 1
    draft = body["drafts"][0]
    assert draft["title"] == "Pedindo comida" and draft["level"] == "A1"

    listed = client.get("/api/course/drafts").json()["drafts"]
    assert [d["id"] for d in listed] == [draft["id"]]
    assert client.get("/api/course").json() == before  # trilha intocada até a aprovação


def test_invalid_output_is_reported_not_saved(client, fake_ollama):
    body = generate(client, fake_ollama, "isto não é json").json()
    assert body["drafts"] == [] and body["failed"] == 1
    assert client.get("/api/course/drafts").json()["drafts"] == []


def test_invalid_exercise_is_dropped_but_the_lesson_is_kept(client, fake_ollama):
    bad = lesson_payload()
    bad["exercises"][3]["words"] = ["bill", "the", "bring", "me", "Can"]  # "me" não está na frase
    body = generate(client, fake_ollama, bad).json()
    assert body["failed"] == 0 and len(body["drafts"]) == 1
    assert len(body["drafts"][0]["exercises"]) == 4


def test_lesson_with_too_few_valid_exercises_is_rejected(client, fake_ollama):
    bad = lesson_payload()
    bad["exercises"][0]["options"] = ["Can"]  # múltipla escolha com uma opção só
    bad["exercises"][1]["answers"] = []
    bad["exercises"][2]["answers"] = []
    body = generate(client, fake_ollama, bad).json()
    assert body["failed"] == 1 and body["drafts"] == []
    assert body["problems"]


def test_approve_adds_the_lesson_to_the_trilha_and_saves_it_on_disk(client, fake_ollama, client_factory, config):
    draft = generate(client, fake_ollama, lesson_payload()).json()["drafts"][0]
    before = 0

    approved = client.post(f"/api/course/drafts/{draft['id']}/approve")
    assert approved.status_code == 200
    lesson_id = approved.json()["lesson_id"]

    # A lição nova fica bloqueada até a anterior ser concluída (regra da trilha), por isso
    # a verificação é pela visão geral, não pelo acesso à lição.
    overview = client.get("/api/course").json()
    a1 = next(level for level in overview["levels"] if level["code"] == "A1")
    assert a1["units"][-1]["id"] == "a1-usuario"
    assert len(a1["units"][-1]["lessons"]) == before + 1
    assert client.get("/api/course/drafts").json()["drafts"] == []
    saved = config.data_dir / "curriculo_usuario" / "en" / "a1.json"
    assert saved.exists() and lesson_id in saved.read_text(encoding="utf-8")


def test_second_approval_appends_to_the_same_user_unit(client, fake_ollama):
    first = generate(client, fake_ollama, lesson_payload("Primeira")).json()["drafts"][0]
    second = generate(client, fake_ollama, lesson_payload("Segunda")).json()["drafts"][0]
    client.post(f"/api/course/drafts/{first['id']}/approve")
    client.post(f"/api/course/drafts/{second['id']}/approve")
    a1 = next(l for l in client.get("/api/course").json()["levels"] if l["code"] == "A1")
    titles = [lesson["title"] for lesson in a1["units"][-1]["lessons"]]
    assert titles == ["Primeira", "Segunda"]


def test_discard_removes_the_draft(client, fake_ollama):
    draft = generate(client, fake_ollama, lesson_payload()).json()["drafts"][0]
    assert client.delete(f"/api/course/drafts/{draft['id']}").status_code == 200
    assert client.get("/api/course/drafts").json()["drafts"] == []
    assert client.delete(f"/api/course/drafts/{draft['id']}").status_code == 404


def test_failed_approval_rolls_back_the_file_and_keeps_the_draft(client, fake_ollama, monkeypatch, config):
    draft = generate(client, fake_ollama, lesson_payload()).json()["drafts"][0]

    def broken_reload(*args, **kwargs):
        raise CurriculumError("conteúdo inválido de teste")

    registry = client.app.state.container.curriculum
    monkeypatch.setattr(registry, "reload", broken_reload)

    response = client.post(f"/api/course/drafts/{draft['id']}/approve")
    assert response.status_code == 400
    assert not (config.data_dir / "curriculo_usuario" / "en" / "a1.json").exists()
    assert len(client.get("/api/course/drafts").json()["drafts"]) == 1
