"""Carrega e valida o currículo (arquivos ``<nível>.json`` desta pasta).

A validação roda na inicialização: um exercício mal formado derruba o backend
com uma mensagem clara, em vez de aparecer quebrado para o aluno.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

EXERCISE_TYPES = ("multiple_choice", "fill_blank", "translate", "reorder", "listen", "open_reply")
MIN_EXERCISES_PER_LESSON = 3


class CurriculumError(ValueError):
    """Conteúdo do currículo inválido."""


@dataclass(frozen=True)
class Exercise:
    id: str
    type: str
    prompt: str
    lesson_id: str
    data: dict[str, Any]

    @property
    def answers(self) -> list[str]:
        return [str(a) for a in self.data.get("answers", [])]

    @property
    def explanation(self) -> str:
        return str(self.data.get("explanation", ""))

    @property
    def hint(self) -> str | None:
        return self.data.get("hint")


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    objective: str
    explanation: str
    key_phrases: tuple[dict[str, str], ...]
    exercises: tuple[Exercise, ...]
    unit_id: str
    level: str
    index: int  # posição global na trilha (0 = primeira lição do A1)


@dataclass(frozen=True)
class Unit:
    id: str
    title: str
    goal: str
    lessons: tuple[Lesson, ...]


@dataclass(frozen=True)
class Level:
    code: str
    title: str
    description: str
    goal: str
    units: tuple[Unit, ...]


class Curriculum:
    """Trilha completa, imutável, com índices por lição e exercício."""

    def __init__(self, levels: tuple[Level, ...]) -> None:
        self.levels = levels
        self.lessons: tuple[Lesson, ...] = tuple(
            lesson for level in levels for unit in level.units for lesson in unit.lessons
        )
        self._lessons = {lesson.id: lesson for lesson in self.lessons}
        self._exercises = {ex.id: ex for lesson in self.lessons for ex in lesson.exercises}

    def lesson(self, lesson_id: str) -> Lesson | None:
        return self._lessons.get(lesson_id)

    def exercise(self, exercise_id: str) -> Exercise | None:
        return self._exercises.get(exercise_id)

    @property
    def exercise_count(self) -> int:
        return len(self._exercises)

    @classmethod
    def load(cls, directory: Path) -> Curriculum:
        return cls.load_many([directory])

    @classmethod
    def load_many(cls, directories: list[Path]) -> Curriculum:
        """Lê os arquivos de várias pastas (ex.: o currículo oficial e as lições criadas pelo usuário).

        A ordem é a das pastas, depois a dos arquivos. Unidades de um mesmo nível são somadas.
        """
        files = [p for directory in directories for p in sorted(directory.glob("*.json"))]
        if not files:
            raise CurriculumError(f"Nenhum arquivo de currículo em {', '.join(str(d) for d in directories)}.")
        levels = _merge_levels([_parse_level(json.loads(p.read_text(encoding="utf-8"))) for p in files])
        _validate_levels(levels)
        return cls(_assign_indexes(levels))


# ----- leitura ---------------------------------------------------------------

def _parse_level(raw: dict[str, Any]) -> Level:
    units = tuple(
        Unit(
            id=unit_raw["id"],
            title=unit_raw["title"],
            goal=unit_raw["goal"],
            lessons=tuple(_parse_lesson(lesson_raw, raw["level"], unit_raw["id"]) for lesson_raw in unit_raw["lessons"]),
        )
        for unit_raw in raw["units"]
    )
    return Level(raw["level"], raw["title"], raw["description"], raw["goal"], units)


def _parse_lesson(raw: dict[str, Any], level: str, unit_id: str) -> Lesson:
    exercises = tuple(Exercise(ex["id"], ex["type"], ex["prompt"], raw["id"], ex) for ex in raw["exercises"])
    return Lesson(
        id=raw["id"],
        title=raw["title"],
        objective=raw["objective"],
        explanation=raw["explanation"],
        key_phrases=tuple(raw.get("key_phrases", [])),
        exercises=exercises,
        unit_id=unit_id,
        level=level,
        index=-1,
    )


def _merge_levels(parsed: list[Level]) -> list[Level]:
    """Um nível pode ter vários arquivos (ex.: ``a1.json`` e ``a1_conversa.json``).

    As unidades são reunidas na ordem dos arquivos; o título e a descrição vêm do primeiro.
    """
    merged: dict[str, Level] = {}
    for level in parsed:
        if level.code not in merged:
            merged[level.code] = level
        else:
            base = merged[level.code]
            merged[level.code] = replace(base, units=base.units + level.units)
    return list(merged.values())


# ----- validação -------------------------------------------------------------

def _validate_levels(levels: list[Level]) -> None:
    seen_lessons: set[str] = set()
    seen_exercises: set[str] = set()
    for level in levels:
        if not level.units:
            raise CurriculumError(f"Nível {level.code} sem unidades.")
        for unit in level.units:
            for lesson in unit.lessons:
                if lesson.id in seen_lessons:
                    raise CurriculumError(f"Lição duplicada: {lesson.id}")
                seen_lessons.add(lesson.id)
                if len(lesson.exercises) < MIN_EXERCISES_PER_LESSON:
                    raise CurriculumError(
                        f"{lesson.id} precisa de pelo menos {MIN_EXERCISES_PER_LESSON} exercícios."
                    )
                for ex in lesson.exercises:
                    if ex.id in seen_exercises:
                        raise CurriculumError(f"Exercício duplicado: {ex.id}")
                    seen_exercises.add(ex.id)
                    _validate_exercise(ex)


def check_lesson(raw: dict[str, Any], level: str) -> None:
    """Valida uma lição isolada (mesmas regras do currículo). Lança CurriculumError se houver problema."""
    lesson = _parse_lesson(raw, level, unit_id="")
    if len(lesson.exercises) < MIN_EXERCISES_PER_LESSON:
        raise CurriculumError(f"{lesson.id} precisa de pelo menos {MIN_EXERCISES_PER_LESSON} exercícios.")
    for ex in lesson.exercises:
        _validate_exercise(ex)


def check_exercise(raw: dict[str, Any], lesson_id: str) -> None:
    """Valida um exercício isolado (usado para descartar só os exercícios inválidos de uma lição gerada)."""
    ex = Exercise(raw["id"], raw["type"], raw["prompt"], lesson_id, raw)
    _validate_exercise(ex)


def _validate_exercise(ex: Exercise) -> None:
    where = f"{ex.lesson_id}/{ex.id}"
    if ex.type not in EXERCISE_TYPES:
        raise CurriculumError(f"{where}: tipo desconhecido '{ex.type}'.")
    if not ex.prompt.strip():
        raise CurriculumError(f"{where}: enunciado vazio.")

    if ex.type == "multiple_choice":
        options = ex.data.get("options", [])
        answer = ex.data.get("answer")
        if not isinstance(options, list) or len(options) < 2:
            raise CurriculumError(f"{where}: múltipla escolha precisa de pelo menos 2 opções.")
        if not isinstance(answer, int) or not 0 <= answer < len(options):
            raise CurriculumError(f"{where}: índice de resposta inválido.")
        return

    if not ex.answers or any(not a.strip() for a in ex.answers):
        raise CurriculumError(f"{where}: lista de respostas aceitas vazia ou com item em branco.")

    if ex.type == "listen":
        text = str(ex.data.get("text", ""))
        if not text.strip():
            raise CurriculumError(f"{where}: exercício de escuta sem texto.")
        if normalize(text) not in {normalize(a) for a in ex.answers}:
            raise CurriculumError(f"{where}: o texto ditado precisa estar entre as respostas aceitas.")

    if ex.type == "reorder":
        words = ex.data.get("words", [])
        if not isinstance(words, list) or len(words) < 2:
            raise CurriculumError(f"{where}: ordenação precisa de palavras.")
        # Os mesmos tokens das palavras embaralhadas devem formar a frase correta.
        if sorted(normalize(" ".join(words)).split()) != sorted(normalize(ex.answers[0]).split()):
            raise CurriculumError(f"{where}: as palavras não formam a frase da resposta.")


def _assign_indexes(levels: list[Level]) -> tuple[Level, ...]:
    """Define a posição global de cada lição (a trilha é sequencial, do A1 ao C1)."""
    position = 0
    result: list[Level] = []
    for level in levels:
        units: list[Unit] = []
        for unit in level.units:
            lessons: list[Lesson] = []
            for lesson in unit.lessons:
                lessons.append(replace(lesson, index=position))
                position += 1
            units.append(replace(unit, lessons=tuple(lessons)))
        result.append(replace(level, units=tuple(units)))
    return tuple(sorted(result, key=lambda lv: lv.code))


# ----- utilidades de resposta ------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s']")


def normalize(text: str, keep_accents: bool = False) -> str:
    """Forma canônica para comparar respostas: minúsculas, sem pontuação.

    Em inglês os acentos são ignorados. Em francês eles mudam a palavra (é ≠ e),
    então ``keep_accents=True`` os preserva. Apóstrofos são mantidos, para diferenciar
    *it's* de *its*.
    """
    text = text.replace("’", "'")
    if not keep_accents:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
    text = _PUNCT_RE.sub(" ", text.lower())
    return " ".join(text.split())


def shuffled_words(exercise: Exercise) -> list[str]:
    """Palavras embaralhadas de forma estável (mesma ordem em toda requisição)."""
    original = list(exercise.data["words"])
    words = list(original)
    rng = random.Random(exercise.id)
    for _ in range(10):
        rng.shuffle(words)
        if words != original:
            break
    return words
