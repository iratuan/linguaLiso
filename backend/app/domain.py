"""Constantes do domínio e modelos de dados validados."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LEVELS = ("A1", "A2", "B1", "B2", "C1")
Level = Literal["A1", "A2", "B1", "B2", "C1"]

MODES = (
    "free",
    "guided_lesson",
    "grammar",
    "vocabulary",
    "roleplay",
    "error_review",
    "listening",
)
Mode = Literal["free", "guided_lesson", "grammar", "vocabulary", "roleplay", "error_review", "listening"]

ROLEPLAY_SCENARIOS: dict[str, str] = {
    "airport": "Aeroporto: check-in, controle de segurança e embarque.",
    "hotel": "Hotel: reserva, check-in, pedidos de serviço e check-out.",
    "restaurant": "Restaurante: pedir comida, pagar a conta e tirar dúvidas do cardápio.",
    "shopping": "Compras: perguntar preços, tamanhos e trocas em uma loja.",
    "travel": "Viagem: pedir informações, transporte e direções.",
    "job_interview": "Entrevista de emprego: apresentação, experiências e perguntas comportamentais.",
    "work_meeting": "Reunião profissional: atualizações de projeto, opiniões e combinados.",
    "small_talk": "Conversa cotidiana: assuntos leves, rotina e opiniões.",
    "customer_service": "Atendimento ao cliente: resolver um problema com um produto ou serviço.",
}

ERROR_CATEGORIES = ("grammar", "vocabulary", "context", "spelling", "other")
SEVERITIES = ("minor", "moderate", "major")

# Intervalos da revisão espaçada (caixas 0..5), em dias.
SRS_INTERVALS_DAYS: tuple[int, ...] = (1, 3, 7, 14, 30, 60)

ENGLISH_VARIANTS = ("american", "british")


class CorrectionData(BaseModel):
    """Correção devolvida pelo professor. Todos os campos são obrigatórios no
    JSON Schema para estabilizar a saída do modelo; quando não há erro,
    ``has_error`` é falso e os demais campos ficam vazios."""

    has_error: bool = False
    original_text: str = ""
    corrected_text: str = ""
    explanation_pt: str = ""
    error_category: Literal["grammar", "vocabulary", "context", "spelling", "other"] = "other"
    severity: Literal["minor", "moderate", "major"] = "minor"
    example_sentence: str = ""
    practice_prompt: str = ""


class NewVocabularyItem(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    translation_pt: str = Field(default="", max_length=200)
    example_sentence: str = Field(default="", max_length=300)


class TeacherTurn(BaseModel):
    """Resposta completa do professor para um turno."""

    reply: str = Field(min_length=1, max_length=4000)
    correction: CorrectionData | None = None
    new_vocabulary: list[NewVocabularyItem] = Field(default_factory=list, max_length=8)
    # False quando a saída do modelo não pôde ser interpretada e a resposta
    # foi usada como texto puro.
    structured: bool = True


class ProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=80)
    level: Level = "A1"
    english_variant: Literal["american", "british"] = "american"
    explanation_language: Literal["pt-BR"] = "pt-BR"
    study_minutes_goal: int = Field(default=20, ge=5, le=240)


class ProfileOut(ProfileIn):
    level_is_manual: bool = True
    updated_at: str


class SessionCreate(BaseModel):
    mode: Mode = "free"
    scenario: str | None = None
    title: str = Field(default="", max_length=120)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    input_source: Literal["text", "voice"] = "text"


TEACHER_PERSONAS = ("formal", "descontraido", "nativo")
DEFAULT_PERSONA = "descontraido"


class SettingsIn(BaseModel):
    """Preferências editáveis. Valores ausentes mantêm o que já está salvo."""

    llm_model: str | None = Field(default=None, min_length=1, max_length=120)
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_num_ctx: int | None = Field(default=None, ge=1024, le=32768)
    history_limit: int | None = Field(default=None, ge=2, le=40)
    speech_voice: str | None = Field(default=None, min_length=1, max_length=120)
    target_language: Literal["en", "fr"] | None = None
    speech_rate: float | None = Field(default=None, ge=0.5, le=2.0)
    speech_volume: float | None = Field(default=None, ge=0.0, le=1.0)
    confirm_transcription: bool | None = None
    response_mode: Literal["audio", "text"] | None = None
    teacher_persona: Literal["formal", "descontraido", "nativo"] | None = None
    ui_transparency: int | None = Field(default=None, ge=0, le=80)
    app_theme: Literal["escuro", "papel"] | None = None
