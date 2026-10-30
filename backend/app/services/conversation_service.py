"""Motor de conversação: monta o contexto pedagógico, chama a LLM e persiste o turno."""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.db import utc_now
from app.domain import DEFAULT_PERSONA, ROLEPLAY_SCENARIOS, MessageCreate, SessionCreate
from app.languages import DEFAULT_LANGUAGE
from app.repositories.progress_repo import ProgressRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import ProfileRepository, SettingsRepository
from app.repositories.vocabulary_repo import VocabularyRepository
from app.services.depth import DEEPENING_MODES, depth_guidance
from app.services.loop_guard import RETRY_INSTRUCTION, is_repetition, latest_student_reminder
from app.services.llm_service import OllamaClient
from app.services.prompt_library import PromptLibrary
from app.services.teacher_response import parse_teacher_output, teacher_json_schema

log = logging.getLogger(__name__)


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class BadRequest(Exception):
    pass


class Locked(Exception):
    """Conteúdo ainda não liberado para o aluno (pré-requisito pendente)."""


class ConversationService:
    def __init__(
        self,
        *,
        config: Settings,
        sessions: SessionRepository,
        vocabulary: VocabularyRepository,
        profiles: ProfileRepository,
        settings: SettingsRepository,
        progress: ProgressRepository,
        llm: OllamaClient,
        prompts: PromptLibrary,
    ) -> None:
        self._config = config
        self._sessions = sessions
        self._vocabulary = vocabulary
        self._profiles = profiles
        self._settings = settings
        self._progress = progress
        self._llm = llm
        self._prompts = prompts

    # ----- sessões -------------------------------------------------------

    def create_session(self, data: SessionCreate) -> dict[str, Any]:
        if data.mode == "roleplay":
            if not data.scenario or data.scenario not in ROLEPLAY_SCENARIOS:
                raise BadRequest(f"Escolha um cenário válido: {', '.join(ROLEPLAY_SCENARIOS)}.")
        elif data.scenario:
            raise BadRequest("Cenário só é aceito no modo roleplay.")

        profile = self._profiles.get() or {"level": "A1"}
        settings = self._settings.get_all()
        model = settings["llm_model"] or self._config.default_llm_model
        language = settings.get("target_language") or DEFAULT_LANGUAGE
        persona = settings.get("teacher_persona") or DEFAULT_PERSONA
        title = data.title.strip() or _default_title(data.mode, data.scenario)
        return self._sessions.create(
            mode=data.mode,
            scenario=data.scenario,
            title=title,
            level=profile["level"],
            model=model,
            language=language,
            persona=persona,
        )

    def get_session(self, session_id: int) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFound("Sessão não encontrada.")
        return session

    def end_session(self, session_id: int) -> dict[str, Any]:
        self.get_session(session_id)
        self._sessions.end(session_id)
        return self.get_session(session_id)

    def delete_session(self, session_id: int) -> None:
        if not self._sessions.delete(session_id):
            raise NotFound("Sessão não encontrada.")

    def transcript(self, session_id: int) -> dict[str, Any]:
        session = self.get_session(session_id)
        return {
            "session": session,
            "messages": self._sessions.list_messages(session_id),
            "corrections": self._sessions.list_corrections(session_id),
        }

    # ----- turnos --------------------------------------------------------

    def send_message(self, session_id: int, data: MessageCreate) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session["ended_at"] is not None:
            raise Conflict("Esta sessão já foi encerrada. Inicie uma nova conversa.")

        content = data.content.strip()
        if len(content) > self._config.max_message_chars:
            raise BadRequest(f"A mensagem excede {self._config.max_message_chars} caracteres.")
        if not content:
            raise BadRequest("A mensagem está vazia.")

        user_message_id = self._sessions.add_message(session_id, "user", content, data.input_source)

        settings = self._settings.get_all()
        history_limit = int(settings["history_limit"]) * 2
        history = self._sessions.list_messages(session_id, limit=history_limit)
        messages = self._build_chat(session, settings, history)
        # O último turno é a fala atual do aluno: reforçamos o que deve ser respondido (sem salvar isso).
        if messages and messages[-1]["role"] == "user":
            role = ROLEPLAY_SCENARIOS.get(session.get("scenario") or "") if session["mode"] == "roleplay" else None
            messages[-1] = {**messages[-1], "content": messages[-1]["content"] + latest_student_reminder(content, role)}

        # Se a LLM falhar, a mensagem do aluno já está salva e LLMUnavailable sobe para a API.
        temperature = float(settings["llm_temperature"])
        num_ctx = int(settings["llm_num_ctx"])
        raw = self._llm.chat(
            model=session["model"],
            messages=messages,
            format_schema=teacher_json_schema(),
            temperature=temperature,
            num_ctx=num_ctx,
        )
        turn = parse_teacher_output(raw)

        # Loop: se o professor repetiu uma fala recente, pede uma resposta nova uma vez.
        previous_replies = [m["content"] for m in history if m["role"] == "assistant"]
        if is_repetition(turn.reply, previous_replies):
            log.info("Resposta repetida detectada na sessão %s; pedindo nova resposta.", session_id)
            retry_messages = [
                *messages,
                {"role": "assistant", "content": turn.reply},
                {"role": "user", "content": RETRY_INSTRUCTION},
            ]
            raw = self._llm.chat(
                model=session["model"],
                messages=retry_messages,
                format_schema=teacher_json_schema(),
                temperature=max(temperature, 0.8),
                num_ctx=num_ctx,
            )
            turn = parse_teacher_output(raw)
        assistant_id = self._sessions.add_message(session_id, "assistant", turn.reply)

        correction_record = None
        correction = turn.correction
        if correction and correction.has_error and correction.corrected_text:
            correction_id = self._sessions.add_correction(
                message_id=user_message_id,
                session_id=session_id,
                data={
                    "original_text": correction.original_text or content,
                    "corrected_text": correction.corrected_text,
                    "explanation_pt": correction.explanation_pt,
                    "example_sentence": correction.example_sentence,
                    "practice_prompt": correction.practice_prompt,
                },
                error_category=correction.error_category,
                severity=correction.severity,
            )
            correction_record = {"id": correction_id, **correction.model_dump()}

        vocab_payload = [item.model_dump() for item in turn.new_vocabulary]
        if vocab_payload:
            self._vocabulary.add_many(
                vocab_payload,
                source_session_id=session_id,
                language=session.get("language") or DEFAULT_LANGUAGE,
            )

        return {
            "user_message_id": user_message_id,
            "assistant_message": {
                "id": assistant_id,
                "role": "assistant",
                "content": turn.reply,
                "created_at": utc_now(),
            },
            "correction": correction_record,
            "new_vocabulary": vocab_payload,
            "structured": turn.structured,
        }

    def _build_chat(self, session: dict[str, Any], settings: dict[str, Any], history: list[dict[str, Any]]):
        profile = self._profiles.get() or {"level": "A1", "english_variant": "american", "display_name": ""}
        recurring = ""
        if session["mode"] == "error_review":
            rows = self._progress.recurring_errors(limit=8)
            recurring = "\n".join(
                f"- {r['corrected_text']} ({r['error_category']}): {r['explanation_pt']}" for r in rows
            )
        lang = session.get("language") or DEFAULT_LANGUAGE
        persona = session.get("persona") or DEFAULT_PERSONA
        parts = [self._prompts.system_prompt(lang), self._prompts.persona_prompt(persona)]
        if lang == "en":
            # A variante só se aplica ao inglês (americano ou britânico).
            variant = "inglês americano" if profile["english_variant"] == "american" else "inglês britânico"
            parts.append(f"Variante de inglês do aluno: {variant}.")
        parts.append(
            self._prompts.mode_prompt(
                lang,
                session["mode"],
                level=session["level"],
                recurring_errors=recurring,
                scenario=session.get("scenario"),
            )
        )
        if session["mode"] in DEEPENING_MODES:
            # Conta a conversa inteira: a fala atual já foi salva antes de montar o chat.
            user_turns = self._sessions.count_user_messages(session["id"])
            parts.append(depth_guidance(user_turns, session["level"]))
        system = "\n\n".join(parts)
        chat: list[dict[str, str]] = [{"role": "system", "content": system}]
        for message in history:
            role = "assistant" if message["role"] == "assistant" else "user"
            chat.append({"role": role, "content": message["content"]})
        return chat


def _default_title(mode: str, scenario: str | None) -> str:
    labels = {
        "free": "Conversação livre",
        "guided_lesson": "Aula guiada",
        "grammar": "Gramática",
        "vocabulary": "Vocabulário",
        "roleplay": "Roleplay",
        "error_review": "Revisão de erros",
        "listening": "Treino de escuta",
    }
    base = labels.get(mode, mode)
    if mode == "roleplay" and scenario:
        return f"{base}: {scenario.replace('_', ' ')}"
    return base
