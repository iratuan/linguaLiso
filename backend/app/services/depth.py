"""Profundidade progressiva da conversa.

O professor começa com temas simples e vai aprofundando conforme o aluno avança na conversa.
A orientação é escolhida pelo número de falas do aluno, para o modelo não depender só de bom senso.
"""

from __future__ import annotations

# Modos em que a conversa deve ir se aprofundando. Roleplay e aula guiada seguem o próprio roteiro.
DEEPENING_MODES = frozenset({"free", "grammar", "vocabulary"})


def depth_stage(user_turns: int) -> int:
    """Estágio de 1 a 4 conforme as falas do aluno."""
    if user_turns <= 2:
        return 1
    if user_turns <= 5:
        return 2
    if user_turns <= 9:
        return 3
    return 4


_STAGE_TEXT = {
    1: (
        "Tema inicial: mantenha o assunto simples e pergunte sobre experiências e preferências pessoais "
        "(o que a pessoa gosta, faz ou costuma fazer)."
    ),
    2: (
        "Aprofunde: reaja ao que o aluno disse acrescentando um detalhe seu, e então pergunte o motivo "
        "ou o modo ('Why…?', 'How…?', 'What makes you…?')."
    ),
    3: (
        "Aprofunde mais: peça comparações, opiniões justificadas e situações hipotéticas "
        "('What would you do if…?'). Pode introduzir uma estrutura um pouco acima do nível, "
        "com um exemplo curto."
    ),
    4: (
        "Discuta o tema como uma conversa entre adultos: peça análise, exemplos concretos e um contraponto. "
        "Desafie gentilmente afirmações vagas com uma pergunta de follow-up mais precisa."
    ),
}


def depth_guidance(user_turns: int, level: str) -> str:
    """Bloco de instrução para o turno atual, pronto para entrar no prompt do sistema."""
    stage = depth_stage(user_turns)
    simple_words = "Use frases curtas e vocabulário básico." if level in {"A1", "A2"} else ""
    return (
        f"PROFUNDIDADE DA CONVERSA (estágio {stage} de 4, aluno com {user_turns} falas): "
        f"{_STAGE_TEXT[stage]} {simple_words}\n"
        "Em cada resposta: (1) reaja de forma específica ao que o aluno disse; "
        "(2) faça UMA pergunta que aprofunde o assunto. Não repita a mesma pergunta de outra forma."
    ).strip()
