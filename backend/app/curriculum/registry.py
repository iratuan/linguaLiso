"""Registro de todos os currículos (um por idioma).

Cada idioma fica em ``curriculum/<código>/`` (conteúdo oficial) e, opcionalmente, em
``<dados>/curriculo_usuario/<código>/`` (lições criadas e aprovadas pelo usuário).
Idiomas sem conteúdo ainda não aparecem na trilha. Os IDs de lições e exercícios são
únicos entre idiomas, porque o progresso é guardado pelo ID.
"""

from __future__ import annotations

from pathlib import Path

from app.curriculum.loader import Curriculum, CurriculumError, Exercise, Lesson
from app.languages import LANGUAGES


def _read_curricula(root: Path, extra_root: Path | None) -> dict[str, Curriculum]:
    curricula: dict[str, Curriculum] = {}
    for code in LANGUAGES:
        folders = [base / code for base in (root, extra_root) if base is not None and (base / code).is_dir()]
        if any(any(folder.glob("*.json")) for folder in folders):
            curricula[code] = Curriculum.load_many(folders)
    if not curricula:
        raise CurriculumError(f"Nenhum currículo encontrado em {root}.")
    return curricula


class CurriculumRegistry:
    def __init__(self, curricula: dict[str, Curriculum]) -> None:
        self._install(curricula)

    @classmethod
    def load(cls, root: Path, extra_root: Path | None = None) -> CurriculumRegistry:
        return cls(_read_curricula(root, extra_root))

    def reload(self, root: Path, extra_root: Path | None = None) -> None:
        """Relê os arquivos e substitui o conteúdo no lugar (quem já tem o registro enxerga a mudança).

        Se a leitura falhar, o conteúdo anterior é mantido.
        """
        self._install(_read_curricula(root, extra_root))

    def _install(self, curricula: dict[str, Curriculum]) -> None:
        lesson_index: dict[str, tuple[str, Lesson]] = {}
        exercise_index: dict[str, tuple[str, Exercise]] = {}
        for code, curriculum in curricula.items():
            for lesson in curriculum.lessons:
                if lesson.id in lesson_index:
                    raise CurriculumError(f"Lição duplicada entre idiomas: {lesson.id}")
                lesson_index[lesson.id] = (code, lesson)
                for ex in lesson.exercises:
                    if ex.id in exercise_index:
                        raise CurriculumError(f"Exercício duplicado entre idiomas: {ex.id}")
                    exercise_index[ex.id] = (code, ex)
        self._curricula = dict(curricula)
        self._lesson_index = lesson_index
        self._exercise_index = exercise_index

    def languages(self) -> list[str]:
        """Códigos dos idiomas com trilha disponível, na ordem do cadastro."""
        return [code for code in LANGUAGES if code in self._curricula]

    def get(self, code: str) -> Curriculum:
        if code not in self._curricula:
            raise CurriculumError(f"A trilha de {LANGUAGES[code].name_pt if code in LANGUAGES else code} ainda não está disponível.")
        return self._curricula[code]

    def all_lessons(self) -> list[Lesson]:
        return [lesson for curriculum in self._curricula.values() for lesson in curriculum.lessons]

    def lesson(self, lesson_id: str) -> tuple[str, Lesson] | None:
        return self._lesson_index.get(lesson_id)

    def exercise(self, exercise_id: str) -> tuple[str, Exercise] | None:
        return self._exercise_index.get(exercise_id)
