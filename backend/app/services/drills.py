"""Treino de repetição: carrega as frases de cada contexto e compara a fala transcrita com a frase-alvo.

Importante: o app só recebe o texto transcrito. A comparação mede o que foi reconhecido,
não a pronúncia. Por isso o critério é uma nota de acerto por palavras, e não um julgamento de sotaque.
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.curriculum.loader import normalize
from app.languages import LANGUAGES

DRILLS_DIR = Path(__file__).resolve().parent.parent / "drills"
PASS_SCORE = 85
MAX_ATTEMPTS = 3


@lru_cache(maxsize=8)
def load_packs(language: str) -> tuple[dict[str, Any], ...]:
    if language not in LANGUAGES:
        return ()
    folder = DRILLS_DIR / language
    packs = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        pack = json.loads(path.read_text(encoding="utf-8"))
        if not pack.get("sentences"):
            continue
        packs.append(pack)
    return tuple(packs)


def find_pack(language: str, pack_id: str) -> dict[str, Any] | None:
    return next((p for p in load_packs(language) if p["id"] == pack_id), None)


def score_transcript(expected: str, transcript: str, language: str) -> dict[str, Any]:
    """Compara a transcrição com a frase-alvo palavra por palavra.

    A nota é o número de palavras que coincidem dividido pelo maior dos dois tamanhos,
    então palavras sobrando também penalizam. Acentos são preservados só em francês.
    """
    keep_accents = language == "fr"
    target = normalize(expected, keep_accents).split()
    heard = normalize(transcript, keep_accents).split()
    if not target:
        return {"score": 0, "passed": False, "missing": [], "extra": []}

    matcher = SequenceMatcher(None, target, heard, autojunk=False)
    matched_target = {i for block in matcher.get_matching_blocks() for i in range(block.a, block.a + block.size)}
    matched_heard = {j for block in matcher.get_matching_blocks() for j in range(block.b, block.b + block.size)}
    matched = len(matched_target)
    score = round(100 * matched / max(len(target), len(heard), 1))
    return {
        "score": score,
        "passed": score >= PASS_SCORE,
        "missing": [w for i, w in enumerate(target) if i not in matched_target],
        "extra": [w for j, w in enumerate(heard) if j not in matched_heard],
    }
