"""Carrega os prompts pedagógicos de ``backend/prompts/<idioma>/``.

Os textos ficam fora do código para poderem ser ajustados sem alterar Python.
Todos os métodos recebem o código do idioma-alvo (``en``, ``fr``...).
"""

from __future__ import annotations

from pathlib import Path

from app.domain import ROLEPLAY_SCENARIOS

_MODE_FILES = {
    "free": "conversation.txt",
    "guided_lesson": "conversation.txt",
    "grammar": "grammar.txt",
    "vocabulary": "vocabulary.txt",
    "roleplay": "roleplay.txt",
    "error_review": "error_review.txt",
    "listening": "listening.txt",
}


class PromptLibrary:
    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._cache: dict[tuple[str, str], str] = {}

    def read(self, lang: str, name: str) -> str:
        key = (lang, name)
        if key not in self._cache:
            path = self._dir / lang / name
            if not path.is_file():
                raise FileNotFoundError(f"Prompt ausente para '{lang}': {path}")
            self._cache[key] = path.read_text(encoding="utf-8").strip()
        return self._cache[key]

    def system_prompt(self, lang: str) -> str:
        return self.read(lang, "system_teacher.txt")

    def mode_prompt(
        self,
        lang: str,
        mode: str,
        *,
        level: str,
        recurring_errors: str = "",
        scenario: str | None = None,
    ) -> str:
        text = self.read(lang, _MODE_FILES[mode])
        if mode == "error_review":
            text = text.replace("{recurring_errors}", recurring_errors or "(nenhum erro registrado ainda)")
        if mode == "roleplay" and scenario:
            text += f"\n\nPapel desta simulação: {ROLEPLAY_SCENARIOS.get(scenario, scenario)}"
            # Reforço no fim do prompt, o ponto de maior peso para o modelo: a identidade é o papel, não o professor.
            text += "\nLembrete: você é a pessoa do papel, não o professor. Não se apresente como professor."
        return f"{text}\n\nNível do aluno: {level}."

    def persona_prompt(self, persona: str) -> str:
        """Tom do professor (formal, descontraido ou nativo). Vale para todos os idiomas."""
        path = self._dir / "personas" / f"{persona}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"Personalidade ausente: {path}")
        return path.read_text(encoding="utf-8").strip()

    def lesson_prompt(self, lang: str) -> str:
        return self.read(lang, "lesson.txt")

    def lesson_check_prompt(self, lang: str) -> str:
        return self.read(lang, "lesson_check.txt")

    def conversation_check_prompt(self, lang: str) -> str:
        return self.read(lang, "conversation_check.txt")
