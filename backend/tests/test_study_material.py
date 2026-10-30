"""Material de apoio: regras que o app aplica e o endpoint de geração."""

import json

from app.services.study_material import (
    correction_points,
    tips_from_corrections,
    validate_exercises,
    validate_items,
    validate_summary,
)

CORRECTION_TURN = json.dumps(
    {
        "reply": "Nice! Tell me more.",
        "correction": {
            "has_error": True,
            "original_text": "I goed to school",
            "corrected_text": "I went to school",
            "explanation_pt": "O passado de 'go' é irregular: 'went'.",
            "error_category": "grammar",
            "severity": "moderate",
            "example_sentence": "I went home early.",
            "practice_prompt": "Say what you did yesterday.",
        },
        "new_vocabulary": [],
    }
)

MATERIAL = json.dumps(
    {
        "title": "Seu treino: passado simples",
        "instructions_pt": "Preencha as lacunas com a forma correta.",
        "word_bank": ["went", "bought"],
        "items": [
            {"sentence": "I ______ (1) to school yesterday.", "answers": ["went"]},
            {"sentence": "She ______ (1) a book and ______ (2) it.", "answers": ["bought", "read"]},
            {"sentence": "Broken item with no blanks.", "answers": ["x"]},
        ],
        "summary_points_pt": ["Você praticou o passado simples.", "   ", "Verbos irregulares como 'go'."],
        "exercises": [
            {"kind": "translate", "prompt": "Eu fui para casa.", "options": [], "answer": "I went home."},
            {
                "kind": "multiple_choice",
                "prompt": "She ______ a book yesterday.",
                "options": ["buy", "bought", "buys"],
                "answer": "bought",
            },
            {"kind": "multiple_choice", "prompt": "Quebrado", "options": ["a"], "answer": "a"},
        ],
        "footer_title_pt": "Palavras para revisar",
    }
)


def start_session_with_error(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    fake_ollama.replies.append(CORRECTION_TURN)
    client.post(f"/api/sessions/{sid}/messages", json={"content": "I goed to school yesterday."})
    return sid


def test_validate_items_keeps_only_items_whose_blanks_match_answers():
    items = validate_items(
        [
            {"sentence": "I ______ (1) home.", "answers": ["went"]},
            {"sentence": "I ______ (1) home.", "answers": ["went", "came"]},
            {"sentence": "No blanks here.", "answers": ["x"]},
            {"sentence": "Empty answer ______ (1)", "answers": [""]},
            "not an object",
        ]
    )
    assert items == [{"sentence": "I ______ (1) home.", "answers": ["went"]}]


def test_validate_summary_drops_blank_points_and_caps_the_list():
    assert validate_summary(["Passado simples.", "  ", 3, "Irregulares."]) == ["Passado simples.", "Irregulares."]
    assert validate_summary("não é lista") == []
    assert len(validate_summary([f"ponto {i}" for i in range(20)])) == 6


def test_validate_exercises_checks_answers_against_options():
    exercises = validate_exercises(
        [
            {"kind": "translate", "prompt": "Eu fui.", "options": ["ignored"], "answer": "I went."},
            {"kind": "multiple_choice", "prompt": "She ______ it.", "options": ["bought", "buy"], "answer": "bought"},
            {"kind": "multiple_choice", "prompt": "Resposta fora", "options": ["a", "b"], "answer": "c"},
            {"kind": "multiple_choice", "prompt": "Só uma opção", "options": ["a"], "answer": "a"},
            {"kind": "essay", "prompt": "Tipo desconhecido", "options": [], "answer": "x"},
            {"kind": "translate", "prompt": "", "options": [], "answer": "vazio"},
        ]
    )
    assert exercises == [
        {"kind": "translate", "prompt": "Eu fui.", "options": [], "answer": "I went."},
        {"kind": "multiple_choice", "prompt": "She ______ it.", "options": ["bought", "buy"], "answer": "bought"},
    ]


def test_correction_points_keep_the_full_explanation():
    corrections = [
        {"original_text": "I goed", "corrected_text": "I went", "explanation_pt": "Irregular."},
        {"original_text": "i goed", "corrected_text": "I went", "explanation_pt": "Repetido."},
    ]
    assert correction_points(corrections) == [
        {"wrong": "I goed", "right": "I went", "explanation_pt": "Irregular."}
    ]


def test_tips_come_from_corrections_and_skip_duplicates_and_no_ops():
    corrections = [
        {"original_text": "I goed", "corrected_text": "I went", "explanation_pt": "Irregular."},
        {"original_text": "i goed", "corrected_text": "I went", "explanation_pt": "Repetido."},
        {"original_text": "Same", "corrected_text": "Same", "explanation_pt": "Nada."},
        {"original_text": "", "corrected_text": "", "explanation_pt": ""},
    ]
    assert tips_from_corrections(corrections) == [
        {"wrong": "I goed", "right": "I went", "tip_pt": "Irregular."}
    ]


def test_material_is_built_from_the_conversation_and_has_tips(client, fake_ollama):
    sid = start_session_with_error(client, fake_ollama)
    fake_ollama.replies.append(MATERIAL)

    response = client.post(f"/api/sessions/{sid}/study-material")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == sid
    assert body["title"] == "Seu treino: passado simples"
    assert [i["answers"] for i in body["items"]] == [["went"], ["bought", "read"]]
    assert body["word_bank"] == ["went", "bought"]  # perfil padrão é A1, então o banco aparece
    assert body["summary_points_pt"] == ["Você praticou o passado simples.", "Verbos irregulares como 'go'."]
    assert [e["kind"] for e in body["exercises"]] == ["translate", "multiple_choice"]
    assert body["corrections"] == [
        {
            "wrong": "I goed to school",
            "right": "I went to school",
            "explanation_pt": "O passado de 'go' é irregular: 'went'.",
        }
    ]
    assert body["tips"] == [
        {
            "wrong": "I goed to school",
            "right": "I went to school",
            "tip_pt": "O passado de 'go' é irregular: 'went'.",
        }
    ]


def test_material_request_sends_the_exercise_prompt_and_the_transcript(client, fake_ollama):
    sid = start_session_with_error(client, fake_ollama)
    fake_ollama.replies.append(MATERIAL)
    client.post(f"/api/sessions/{sid}/study-material")

    request = fake_ollama.requests[-1]
    prompt = request["messages"][0]["content"]
    assert "exercício de preenchimento de lacunas" in prompt
    assert '"corrections"' in prompt and "I goed to school yesterday." in prompt
    assert request["format"]["required"] == [
        "title",
        "instructions_pt",
        "word_bank",
        "items",
        "summary_points_pt",
        "exercises",
        "footer_title_pt",
    ]


def test_session_without_student_turns_is_refused(client, fake_ollama):
    sid = client.post("/api/sessions", json={"mode": "free"}).json()["id"]
    response = client.post(f"/api/sessions/{sid}/study-material")
    assert response.status_code == 400


def test_unusable_model_output_is_refused_without_crashing(client, fake_ollama):
    sid = start_session_with_error(client, fake_ollama)
    fake_ollama.replies.append('{"title": "x", "items": []}')
    response = client.post(f"/api/sessions/{sid}/study-material")
    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_unknown_session_is_not_found(client):
    assert client.post("/api/sessions/9999/study-material").status_code == 404
