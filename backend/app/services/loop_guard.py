"""Proteção contra loops: o professor não pode repetir a mesma fala ignorando o aluno.

O modelo tende a copiar a última resposta do histórico. Quando isso acontece, o app pede uma
nova resposta com uma instrução explícita e, na montagem do chat, reforça a última fala do aluno.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from app.curriculum.loader import normalize

SIMILARITY_LIMIT = 0.85
RECENT_REPLIES = 2

RETRY_INSTRUCTION = (
    "ATENÇÃO: sua resposta anterior repetiu uma fala já feita. Não repita. "
    "Reaja de forma específica ao que o aluno acabou de dizer e faça uma pergunta diferente, "
    "que avance a conversa."
)


def is_repetition(reply: str, previous_replies: list[str]) -> bool:
    """True quando a resposta é praticamente igual a uma das respostas recentes do professor."""
    current = normalize(reply)
    if not current:
        return False
    for previous in previous_replies[-RECENT_REPLIES:]:
        past = normalize(previous)
        if not past:
            continue
        if current == past or SequenceMatcher(None, current, past).ratio() >= SIMILARITY_LIMIT:
            return True
    return False


def latest_student_reminder(content: str, role: str | None = None) -> str:
    """Lembrete acrescentado só ao pedido enviado ao modelo (não é salvo no histórico).

    Em roleplay, ``role`` lembra o papel que deve ser mantido em cada turno.
    """
    text = f'\n\n(Responda ao que o aluno acabou de dizer: "{content}". Não repita a pergunta anterior.)'
    if role:
        text += f"\n(Continue no papel: {role}. Não se apresente como professor.)"
    return text
