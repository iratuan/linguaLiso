"""Interpretação da saída do modelo.

O Ollama recebe um JSON Schema e tenta devolver JSON válido. Mesmo assim, a
saída pode vir malformada, truncada ou com texto ao redor. Esta função nunca
lança exceção: se a estrutura não puder ser lida, a resposta vira texto puro
e a sessão continua.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from app.domain import TeacherTurn

log = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def teacher_json_schema() -> dict:
    """JSON Schema enviado ao Ollama no parâmetro ``format``."""
    correction = {
        "type": "object",
        "properties": {
            "has_error": {"type": "boolean"},
            "original_text": {"type": "string"},
            "corrected_text": {"type": "string"},
            "explanation_pt": {"type": "string"},
            "error_category": {"type": "string", "enum": ["grammar", "vocabulary", "context", "spelling", "other"]},
            "severity": {"type": "string", "enum": ["minor", "moderate", "major"]},
            "example_sentence": {"type": "string"},
            "practice_prompt": {"type": "string"},
        },
        "required": [
            "has_error",
            "original_text",
            "corrected_text",
            "explanation_pt",
            "error_category",
            "severity",
            "example_sentence",
            "practice_prompt",
        ],
    }
    vocabulary_item = {
        "type": "object",
        "properties": {
            "term": {"type": "string"},
            "translation_pt": {"type": "string"},
            "example_sentence": {"type": "string"},
        },
        "required": ["term", "translation_pt", "example_sentence"],
    }
    return {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "correction": correction,
            "new_vocabulary": {"type": "array", "items": vocabulary_item},
        },
        "required": ["reply", "correction", "new_vocabulary"],
    }


def parse_teacher_output(raw: str) -> TeacherTurn:
    """Converte a saída bruta do modelo em ``TeacherTurn``.

    Ordem de tentativas: JSON direto, JSON dentro de cerca de código, primeiro
    objeto JSON encontrado no texto. Se nada funcionar, devolve o texto como
    resposta sem correção.
    """
    cleaned = _THINK_RE.sub("", raw or "").strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()

    for candidate in _candidates(cleaned):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        data = _normalize(data)
        try:
            return TeacherTurn.model_validate({**data, "structured": True})
        except ValidationError as exc:
            log.warning("JSON do modelo não passou na validação: %s", exc.error_count())

    fallback_text = cleaned or "Desculpe, não consegui gerar uma resposta. Tente novamente."
    return TeacherTurn(reply=fallback_text[:4000], correction=None, new_vocabulary=[], structured=False)


def parse_json_object(raw: str) -> dict | None:
    """Extrai o primeiro objeto JSON da saída, ou ``None`` se não houver nenhum."""
    cleaned = _THINK_RE.sub("", raw or "").strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()
    for candidate in _candidates(cleaned):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _candidates(text: str) -> list[str]:
    if not text:
        return []
    found = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        found.append(text[start : end + 1])
    return found


def _normalize(data: dict) -> dict:
    """Aceita pequenas variações comuns de chave e remove valores nulos perigosos."""
    reply = data.get("reply") or data.get("response") or data.get("text") or ""
    correction = data.get("correction")
    if isinstance(correction, dict) and not correction.get("has_error", False):
        correction = None
    vocab = data.get("new_vocabulary") or []
    if not isinstance(vocab, list):
        vocab = []
    cleaned_vocab = [
        {
            "term": str(item.get("term", "")).strip(),
            "translation_pt": str(item.get("translation_pt", "")),
            "example_sentence": str(item.get("example_sentence", "")),
        }
        for item in vocab
        if isinstance(item, dict) and str(item.get("term", "")).strip()
    ]
    return {"reply": str(reply).strip(), "correction": correction, "new_vocabulary": cleaned_vocab}
