"""Trilha de curso: visão geral, bloqueio sequencial, correção e conclusão das lições.

Regras:
- As lições de um idioma são sequenciais, do nível inicial ao avançado. A próxima só libera
  quando a anterior for concluída.
- Uma lição é concluída com pelo menos ``PASS_SCORE`` % de acertos nos exercícios.
- Exercícios fechados (múltipla escolha, completar, ordenar, ditado) são corrigidos
  localmente pela comparação normalizada. Respostas abertas (tradução e conversa) que não
  batem exatamente com a referência são avaliadas pela LLM, que aceita variações equivalentes.
- A trilha exibida é a do idioma-alvo escolhido nos ajustes. As respostas usam o idioma da
  própria lição, então um exercício de outro idioma continua corrigido corretamente.
"""

from __future__ import annotations

import logging
from typing import Any

from app.curriculum.loader import Curriculum, CurriculumError, Exercise, Lesson, normalize, shuffled_words
from app.curriculum.registry import CurriculumRegistry
from app.languages import DEFAULT_LANGUAGE, LANGUAGES
from app.repositories.course_repo import CourseRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.conversation_service import BadRequest, Conflict, Locked, NotFound
from app.services.lesson_service import VERDICT_SCHEMA, AnswerVerdict
from app.services.llm_service import LLMUnavailable, OllamaClient
from app.services.prompt_library import PromptLibrary
from app.services.speech_client import SpeechClient
from app.services.teacher_response import parse_json_object

log = logging.getLogger(__name__)

PASS_SCORE = 70
# Tipos cuja resposta fora da lista de referência é avaliada pela LLM.
AI_JUDGED_TYPES = ("translate", "open_reply")
STATUS_LOCKED = "locked"
STATUS_AVAILABLE = "available"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class CourseService:
    def __init__(
        self,
        *,
        registry: CurriculumRegistry,
        repo: CourseRepository,
        settings: SettingsRepository,
        llm: OllamaClient,
        prompts: PromptLibrary,
        speech: SpeechClient,
        default_model: str,
    ) -> None:
        self._registry = registry
        self._repo = repo
        self._settings = settings
        self._llm = llm
        self._prompts = prompts
        self._speech = speech
        self._default_model = default_model

    # ----- idioma ativo -----------------------------------------------------

    def active_language(self) -> str:
        return self._settings.get_all().get("target_language") or DEFAULT_LANGUAGE

    def _active_curriculum(self) -> tuple[str, Curriculum]:
        code = self.active_language()
        try:
            return code, self._registry.get(code)
        except CurriculumError as exc:
            raise BadRequest(str(exc)) from exc

    def _locate_lesson(self, lesson_id: str) -> tuple[str, Lesson]:
        found = self._registry.lesson(lesson_id)
        if found is None:
            raise NotFound("Lição não encontrada.")
        return found

    # ----- estado -----------------------------------------------------------

    def _lesson_states(self, curriculum: Curriculum) -> dict[str, dict[str, Any]]:
        """Status, nota e bloqueio de cada lição do idioma, na ordem da trilha."""
        progress = self._repo.lesson_progress()
        started = self._repo.started_lessons()
        states: dict[str, dict[str, Any]] = {}
        previous_completed = True
        for lesson in curriculum.lessons:
            row = progress.get(lesson.id)
            completed = bool(row and row["completed"])
            locked = not (previous_completed or completed)
            if completed:
                status = STATUS_COMPLETED
            elif locked:
                status = STATUS_LOCKED
            elif lesson.id in started:
                status = STATUS_IN_PROGRESS
            else:
                status = STATUS_AVAILABLE
            states[lesson.id] = {
                "status": status,
                "locked": locked,
                "score": row["score"] if row else None,
                "completed_at": row["completed_at"] if row else None,
            }
            previous_completed = completed
        return states

    def _require_unlocked(self, curriculum: Curriculum, lesson_id: str) -> dict[str, dict[str, Any]]:
        states = self._lesson_states(curriculum)
        if states[lesson_id]["locked"]:
            raise Locked("Esta lição ainda está bloqueada. Conclua a anterior primeiro.")
        return states

    # ----- visão geral ------------------------------------------------------

    def overview(self) -> dict[str, Any]:
        code, curriculum = self._active_curriculum()
        states = self._lesson_states(curriculum)
        total = len(curriculum.lessons)
        completed = sum(1 for s in states.values() if s["status"] == STATUS_COMPLETED)
        levels = []
        for level in curriculum.levels:
            units = []
            for unit in level.units:
                lessons = [
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "objective": lesson.objective,
                        "position": lesson.index + 1,
                        "exercise_count": len(lesson.exercises),
                        **states[lesson.id],
                    }
                    for lesson in unit.lessons
                ]
                units.append({"id": unit.id, "title": unit.title, "goal": unit.goal, "lessons": lessons})
            level_done = [states[lesson.id]["status"] == STATUS_COMPLETED for unit in level.units for lesson in unit.lessons]
            levels.append(
                {
                    "code": level.code,
                    "title": level.title,
                    "description": level.description,
                    "goal": level.goal,
                    "completed": sum(level_done),
                    "total": len(level_done),
                    "units": units,
                }
            )
        return {
            "language": {"code": code, "name": LANGUAGES[code].name_pt},
            "levels": levels,
            "progress": {
                "completed": completed,
                "total": total,
                "percent": round(100 * completed / total) if total else 0,
            },
            "next_lesson_id": self._next_lesson_id(curriculum, states),
            "pass_score": PASS_SCORE,
        }

    def _next_lesson_id(self, curriculum: Curriculum, states: dict[str, dict[str, Any]]) -> str | None:
        for lesson in curriculum.lessons:
            if states[lesson.id]["status"] != STATUS_COMPLETED:
                return lesson.id
        return None

    # ----- lição ------------------------------------------------------------

    def lesson(self, lesson_id: str) -> dict[str, Any]:
        code, lesson = self._locate_lesson(lesson_id)
        curriculum = self._registry.get(code)
        states = self._require_unlocked(curriculum, lesson_id)
        results = self._repo.exercise_results(lesson_id)
        exercises = [self._public_exercise(ex, results.get(ex.id)) for ex in lesson.exercises]
        answered = sum(1 for e in exercises if e["answered"])
        return {
            "id": lesson.id,
            "language": code,
            "title": lesson.title,
            "objective": lesson.objective,
            "explanation": lesson.explanation,
            "key_phrases": list(lesson.key_phrases),
            "level": lesson.level,
            "unit_id": lesson.unit_id,
            "position": lesson.index + 1,
            **states[lesson_id],
            "pass_score": PASS_SCORE,
            "answered": answered,
            "can_complete": answered == len(exercises),
            "exercises": exercises,
            "next_lesson_id": self._next_after(curriculum, lesson),
        }

    def _next_after(self, curriculum: Curriculum, lesson: Lesson) -> str | None:
        lessons = curriculum.lessons
        return lessons[lesson.index + 1].id if lesson.index + 1 < len(lessons) else None

    def _public_exercise(self, ex: Exercise, result: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": ex.id,
            "type": ex.type,
            "prompt": ex.prompt,
            "hint": ex.hint,
            "answered": result is not None,
            "correct": None if result is None else bool(result["correct"]),
            "last_answer": None if result is None else result["last_answer"],
        }
        if ex.data.get("context"):
            payload["context"] = ex.data["context"]
        if ex.type == "multiple_choice":
            payload["options"] = list(ex.data["options"])
        elif ex.type == "reorder":
            payload["words"] = shuffled_words(ex)
        elif ex.type == "listen":
            payload["has_audio"] = True
        return payload

    # ----- correção ---------------------------------------------------------

    def check(self, exercise_id: str, answer: Any) -> dict[str, Any]:
        found = self._registry.exercise(exercise_id)
        if found is None:
            raise NotFound("Exercício não encontrado.")
        code, exercise = found
        lesson_code, lesson = self._locate_lesson(exercise.lesson_id)
        curriculum = self._registry.get(lesson_code)
        # Lições concluídas também podem ser refeitas: as respostas novas substituem as antigas.
        self._require_unlocked(curriculum, lesson.id)

        keep_accents = LANGUAGES[code].accent_sensitive
        if exercise.type == "multiple_choice":
            if not isinstance(answer, int) or isinstance(answer, bool):
                raise BadRequest("Escolha uma das opções.")
            options = exercise.data["options"]
            if not 0 <= answer < len(options):
                raise BadRequest("Opção inválida.")
            correct = answer == exercise.data["answer"]
            stored = options[answer]
            correct_answer = options[exercise.data["answer"]]
            feedback = _feedback(correct, exercise)
            used_ai = False
        else:
            text = "" if answer is None else str(answer).strip()
            if not text:
                raise BadRequest("Escreva uma resposta antes de verificar.")
            stored = text
            correct = normalize(text, keep_accents) in {normalize(a, keep_accents) for a in exercise.answers}
            used_ai = False
            feedback = None
            if not correct and exercise.type in AI_JUDGED_TYPES:
                verdict = self._ai_verdict(code, exercise, text)
                if verdict is not None:
                    used_ai = True
                    correct = verdict.is_correct
                    feedback = verdict.feedback_pt or None
            if feedback is None:
                feedback = _feedback(correct, exercise)
            correct_answer = exercise.answers[0]

        self._repo.save_exercise_result(lesson.id, exercise.id, correct, stored)
        self._repo.log_attempt(lesson.id, exercise.id, exercise.type, correct, stored)
        return {
            "correct": correct,
            "feedback_pt": feedback,
            "correct_answer": None if correct else correct_answer,
            "used_ai_check": used_ai,
        }

    def _ai_verdict(self, code: str, exercise: Exercise, text: str) -> AnswerVerdict | None:
        """Pede à LLM que avalie uma resposta fora da lista de referência. None se indisponível."""
        settings = self._settings.get_all()
        template = (
            self._prompts.conversation_check_prompt(code)
            if exercise.type == "open_reply"
            else self._prompts.lesson_check_prompt(code)
        )
        prompt = template.format(
            prompt=exercise.prompt,
            expected=exercise.answers[0],
            answer=text,
            examples="; ".join(exercise.answers[:4]),
            context=exercise.data.get("context", ""),
        )
        try:
            raw = self._llm.chat(
                model=settings["llm_model"] or self._default_model,
                messages=[{"role": "user", "content": prompt}],
                format_schema=VERDICT_SCHEMA,
                temperature=0.1,
                num_ctx=int(settings["llm_num_ctx"]),
            )
        except LLMUnavailable as exc:
            log.info("Avaliação por IA indisponível (%s); usando comparação literal.", exc.code)
            return None
        data = parse_json_object(raw)
        if data is None:
            return None
        try:
            return AnswerVerdict.model_validate(data)
        except ValueError:
            return None

    # ----- conclusão --------------------------------------------------------

    def complete(self, lesson_id: str) -> dict[str, Any]:
        code, lesson = self._locate_lesson(lesson_id)
        curriculum = self._registry.get(code)
        states = self._require_unlocked(curriculum, lesson_id)
        results = self._repo.exercise_results(lesson_id)
        missing = [ex.id for ex in lesson.exercises if ex.id not in results]
        if missing:
            raise BadRequest(f"Responda todos os exercícios antes de concluir (faltam {len(missing)}).")

        total = len(lesson.exercises)
        correct = sum(1 for ex in lesson.exercises if results[ex.id]["correct"])
        score = round(100 * correct / total)
        passed = score >= PASS_SCORE
        progress = self._repo.finish_lesson(lesson_id, score, passed)
        return {
            "score": score,
            "passed": passed,
            "correct": correct,
            "total": total,
            "pass_score": PASS_SCORE,
            "completed": bool(progress["completed"]),
            "next_lesson_id": self._next_after(curriculum, lesson) if passed else lesson_id,
        }

    def retry(self, lesson_id: str) -> dict[str, Any]:
        """Limpa as respostas de uma lição não concluída para refazê-la."""
        code, _ = self._locate_lesson(lesson_id)
        self._require_unlocked(self._registry.get(code), lesson_id)
        self._repo.clear_exercise_results(lesson_id)
        return self.lesson(lesson_id)

    # ----- áudio ------------------------------------------------------------

    def listening_audio(self, exercise_id: str) -> bytes:
        found = self._registry.exercise(exercise_id)
        if found is None or found[1].type != "listen":
            raise NotFound("Exercício de escuta não encontrado.")
        code, exercise = found
        self._require_unlocked(self._registry.get(code), exercise.lesson_id)
        settings = self._settings.get_all()
        return self._speech.synthesize(
            str(exercise.data["text"]),
            voice=LANGUAGES[code].voice,
            rate=float(settings["speech_rate"]),
            volume=float(settings["speech_volume"]),
        )


def _feedback(correct: bool, exercise: Exercise) -> str:
    """Explicação pedagógica. O título (“Muito bem!” / “Quase lá”) fica por conta da interface."""
    if exercise.explanation:
        return exercise.explanation
    return "Resposta correta." if correct else "Confira a resposta esperada."
