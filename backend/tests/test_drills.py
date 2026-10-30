"""Treino de repetição: pontuação da fala transcrita e endpoints."""

from app.services.drills import PASS_SCORE, load_packs, score_transcript


def test_exact_repeat_passes_with_full_score():
    result = score_transcript("Can I see the menu?", "can I see the menu", "en")
    assert result["score"] == 100 and result["passed"] is True
    assert result["missing"] == [] and result["extra"] == []


def test_missing_word_is_reported_and_lowers_the_score():
    result = score_transcript("I would like a coffee, please.", "I would like coffee please", "en")
    assert result["missing"] == ["a"]
    assert result["score"] < 100


def test_extra_words_are_penalized():
    result = score_transcript("Can we have the bill?", "Can we have the bill please thank you", "en")
    assert result["passed"] is False
    assert result["extra"] == ["please", "thank", "you"]


def test_empty_transcript_scores_zero():
    result = score_transcript("Hello.", "", "en")
    assert result["score"] == 0 and result["passed"] is False


def test_threshold_is_respected():
    # 5 de 6 palavras = 83%, abaixo do limite
    assert score_transcript("one two three four five six", "one two three four five", "en")["score"] < PASS_SCORE


def test_french_keeps_accents_english_ignores_them():
    assert score_transcript("Je peux voir la carte ?", "je peux voir la carte", "fr")["passed"] is True
    assert score_transcript("Je prends l'été", "Je prends l'ete", "fr")["passed"] is False
    assert score_transcript("Café", "cafe", "en")["passed"] is True


def test_packs_are_complete_and_have_translations():
    for language in ("en", "fr"):
        packs = load_packs(language)
        assert packs, language
        for pack in packs:
            assert pack["id"] and pack["title"] and pack["context"]
            for sentence in pack["sentences"]:
                assert sentence["text"].strip() and sentence["pt"].strip()


def test_api_lists_packs_for_the_active_language_and_scores_repeats(client):
    packs = client.get("/api/drills").json()
    assert packs["language"] == "en"
    assert any(p["id"] == "en-restaurant-a1" for p in packs["packs"])

    detail = client.get("/api/drills/en-restaurant-a1").json()
    assert detail["sentences"][0]["text"]

    right = client.post("/api/drills/score", json={
        "pack_id": "en-restaurant-a1", "sentence_index": 1, "transcript": "Can I see the menu?"}).json()
    assert right["passed"] is True and right["expected"] == "Can I see the menu?"

    wrong = client.post("/api/drills/score", json={
        "pack_id": "en-restaurant-a1", "sentence_index": 1, "transcript": "where is the toilet"}).json()
    assert wrong["passed"] is False


def test_api_switches_to_french_packs(client):
    client.put("/api/settings", json={"target_language": "fr"})
    packs = client.get("/api/drills").json()
    assert packs["language"] == "fr" and packs["packs"][0]["id"] == "fr-restaurant-a1"


def test_unknown_pack_or_sentence_is_404(client):
    assert client.post("/api/drills/score", json={
        "pack_id": "nope", "sentence_index": 0, "transcript": "x"}).status_code == 404
    assert client.post("/api/drills/score", json={
        "pack_id": "en-restaurant-a1", "sentence_index": 99, "transcript": "x"}).status_code == 404
