"""Idiomas-alvo que o aplicativo ensina.

Cada idioma tem a própria pasta de currículo e de prompts, a voz do professor e o
código de reconhecimento de fala. Para adicionar um idioma, cadastre-o aqui e crie
as pastas ``curriculum/<código>/`` e ``prompts/<código>/``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str  # código interno e nome da pasta: "en", "fr"
    name_pt: str  # nome exibido na interface, em português
    teacher_name: str  # nome do idioma escrito no próprio idioma (para os prompts)
    voice: str  # voz do Piper (arquivo em ai-model/voices)
    whisper_language: str  # código de idioma enviado ao faster-whisper
    # Se True, letras acentuadas diferem (é ≠ e). Em inglês não há acento de significado.
    accent_sensitive: bool


LANGUAGES: dict[str, Language] = {
    "en": Language(
        code="en",
        name_pt="Inglês",
        teacher_name="English",
        voice="en_US-lessac-medium",
        whisper_language="en",
        accent_sensitive=False,
    ),
    "fr": Language(
        code="fr",
        name_pt="Francês",
        teacher_name="Français",
        voice="fr_FR-siwis-medium",
        whisper_language="fr",
        accent_sensitive=True,
    ),
}

DEFAULT_LANGUAGE = "en"


def get_language(code: str) -> Language:
    try:
        return LANGUAGES[code]
    except KeyError as exc:
        raise ValueError(f"Idioma não suportado: {code}") from exc
