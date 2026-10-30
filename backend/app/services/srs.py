"""Revisão espaçada de vocabulário (esquema de caixas, estilo Leitner).

Cada item fica em uma caixa de 0 a 5. Os intervalos vêm de ``SRS_INTERVALS_DAYS``:

- ``forgot`` (esqueci): volta para a caixa 0 e aparece amanhã.
- ``hard`` (difícil): permanece na caixa atual (mínimo 1) e usa o intervalo dela.
- ``good`` (lembrei): sobe uma caixa, até a última, e usa o novo intervalo.

Funções puras, sem acesso a banco, para facilitar os testes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.domain import SRS_INTERVALS_DAYS

Rating = Literal["forgot", "hard", "good"]
MAX_BOX = len(SRS_INTERVALS_DAYS) - 1


def next_box(box: int, rating: Rating) -> int:
    if not 0 <= box <= MAX_BOX:
        raise ValueError(f"Caixa inválida: {box}")
    if rating == "forgot":
        return 0
    if rating == "hard":
        return max(1, box)
    if rating == "good":
        return min(box + 1, MAX_BOX)
    raise ValueError(f"Avaliação inválida: {rating}")


def interval_for_box(box: int) -> timedelta:
    return timedelta(days=SRS_INTERVALS_DAYS[box])


def schedule_review(box: int, rating: Rating, now: datetime | None = None) -> tuple[int, datetime]:
    """Retorna ``(nova_caixa, próxima_revisão)``."""
    now = now or datetime.now(timezone.utc)
    new_box = next_box(box, rating)
    return new_box, now + interval_for_box(new_box)
