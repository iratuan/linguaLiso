"""Proteção contra loops: repetição detectada e nova resposta pedida ao modelo."""

import json

from app.services.loop_guard import RETRY_INSTRUCTION, is_repetition, latest_student_reminder


def reply(text):
    return json.dumps({"reply": text, "correction": None, "new_vocabulary": []})


def test_identical_and_near_identical_replies_are_repetitions():
    previous = ["Great, Ira! Tell me about your work experience. Have you worked before?"]
    assert is_repetition(previous[0], previous)
    assert is_repetition("Great, Ira! Tell me about your work experience. Have you worked before", previous)


def test_different_reply_is_not_a_repetition():
    previous = ["Great, Ira! Tell me about your work experience."]
    assert not is_repetition("What did you enjoy most in that job?", previous)


def test_only_the_two_most_recent_replies_count():
    old = "Where are you from?"
    recent = ["What is your job?", "Nice, what did you do there?"]
    assert not is_repetition(old, [old, *recent])
    assert is_repetition("What is your job?", [old, *recent])


def test_empty_reply_is_not_treated_as_repetition():
    assert not is_repetition("", [""])


def test_reminder_quotes_the_students_latest_words():
    text = latest_student_reminder("I worked as a software engineer")
    assert "I worked as a software engineer" in text and "Não repita" in text


def test_repeated_reply_is_replaced_by_a_new_one(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    fake_ollama.replies.append(reply("What is your job?"))
    client.post(f"/api/sessions/{sid}/messages", json={"content": "hello"})

    before = len(fake_ollama.requests)
    # O modelo repete a pergunta anterior; a segunda tentativa traz uma fala nova.
    fake_ollama.replies.extend([reply("What is your job?"), reply("Nice, what did you do there?")])
    turn = client.post(f"/api/sessions/{sid}/messages", json={"content": "I am an engineer"}).json()

    assert turn["assistant_message"]["content"] == "Nice, what did you do there?"
    assert len(fake_ollama.requests) - before == 2
    retry = fake_ollama.requests[-1]["messages"]
    assert retry[-1]["content"] == RETRY_INSTRUCTION


def test_non_repeated_reply_is_not_retried(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    fake_ollama.replies.append(reply("What is your job?"))
    client.post(f"/api/sessions/{sid}/messages", json={"content": "hello"})
    before = len(fake_ollama.requests)
    fake_ollama.replies.append(reply("Interesting. What do you enjoy about it?"))
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I am an engineer"})
    assert len(fake_ollama.requests) - before == 1


def test_roleplay_prompt_overrides_the_teacher_identity(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "roleplay", "scenario": "job_interview"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "Hello"})
    system = fake_ollama.requests[-1]["messages"][0]["content"]
    assert "NÃO é o professor" in system
    assert "Não se apresente como professor" in system


def test_roleplay_turn_reminds_the_model_of_the_persona(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "roleplay", "scenario": "job_interview"}).json()["id"]
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I am ready"})
    last_user = next(
        m for m in reversed(fake_ollama.requests[-1]["messages"]) if m["role"] == "user"
    )
    assert "Continue no papel: Entrevista de emprego" in last_user["content"]
