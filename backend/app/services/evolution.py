"""Curva de evolução do aluno: séries diárias e tendências.

Função pura (sem banco), para ser testada isoladamente. Recebe as linhas
agregadas pelo repositório e devolve as séries prontas para o gráfico.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean
from typing import Any

TREND_WINDOW_DAYS = 7


def _pct(part: float, whole: float) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def _average(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def word_count(text: str) -> int:
    return len(text.split())


def _trend(series: list[dict[str, Any]], key: str) -> dict[str, float | None]:
    """Média dos dias com dados na última janela contra a janela anterior."""
    recent = [d[key] for d in series[-TREND_WINDOW_DAYS:] if d[key] is not None]
    previous = [d[key] for d in series[-2 * TREND_WINDOW_DAYS:-TREND_WINDOW_DAYS] if d[key] is not None]
    return {"recent": _average(recent), "previous": _average(previous)}


def build_evolution(
    *,
    today: date,
    days: int,
    messages: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    vocabulary: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
    lesson_titles: dict[str, str],
) -> dict[str, Any]:
    start = today - timedelta(days=days - 1)
    day_keys = [(start + timedelta(days=i)).isoformat() for i in range(days)]

    words_by_day: dict[str, list[int]] = {}
    for m in messages:
        words_by_day.setdefault(m["day"], []).append(word_count(m["content"]))
    corr = {c["day"]: c["count"] for c in corrections}
    att = {a["day"]: (int(a["correct"] or 0), int(a["total"] or 0)) for a in attempts}
    vocab = {v["day"]: v["count"] for v in vocabulary}
    done_by_day: dict[str, int] = {}
    for lesson in lessons:
        done_by_day[lesson["completed_at"][:10]] = done_by_day.get(lesson["completed_at"][:10], 0) + 1

    # Lições concluídas antes da janela já fazem parte do acumulado inicial.
    lessons_before = sum(1 for lesson in lessons if lesson["completed_at"][:10] < day_keys[0])

    series: list[dict[str, Any]] = []
    cum_lessons = lessons_before
    # O acumulado de vocabulário começa na janela: palavras anteriores não são contadas.
    cum_vocab = 0
    for day in day_keys:
        user_msgs = len(words_by_day.get(day, []))
        errors = corr.get(day, 0)
        correct, total = att.get(day, (0, 0))
        new_lessons = done_by_day.get(day, 0)
        new_vocab = vocab.get(day, 0)
        cum_lessons += new_lessons
        cum_vocab += new_vocab
        series.append(
            {
                "day": day,
                "user_messages": user_msgs,
                "corrections": errors,
                # Acertos da conversa: frases sem correção sobre o total de frases do dia.
                "accuracy": _pct(user_msgs - errors, user_msgs),
                "avg_words": _average(words_by_day.get(day, [])),
                "exercises": total,
                "exercise_accuracy": _pct(correct, total),
                "lessons_completed": new_lessons,
                "vocabulary_added": new_vocab,
                "cumulative_lessons": cum_lessons,
                "cumulative_vocabulary": cum_vocab,
            }
        )

    scores = [
        {
            "lesson_id": row["lesson_id"],
            "title": lesson_titles.get(row["lesson_id"], row["lesson_id"]),
            "score": row["score"],
            "completed_at": row["completed_at"],
        }
        for row in lessons
    ]

    all_messages = sum(d["user_messages"] for d in series)
    all_errors = sum(d["corrections"] for d in series)
    all_exercises = sum(d["exercises"] for d in series)
    all_correct = sum(att.get(d, (0, 0))[0] for d in day_keys)
    all_words = [w for ws in words_by_day.values() for w in ws]

    return {
        "range_days": days,
        "series": series,
        "lesson_scores": scores,
        "trend": {
            "accuracy": _trend(series, "accuracy"),
            "avg_words": _trend(series, "avg_words"),
            "exercise_accuracy": _trend(series, "exercise_accuracy"),
        },
        "totals": {
            "user_messages": all_messages,
            "conversation_accuracy": _pct(all_messages - all_errors, all_messages),
            "exercise_accuracy": _pct(all_correct, all_exercises),
            "avg_words": _average(all_words),
            "lessons_completed": cum_lessons,
        },
    }
