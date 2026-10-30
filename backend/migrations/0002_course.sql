-- Progresso na trilha de curso (conteúdo fixo em app/curriculum/*.json).

-- Uma linha por lição iniciada/concluída.
CREATE TABLE course_lesson_progress (
    lesson_id    TEXT PRIMARY KEY,
    score        INTEGER NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
    completed    INTEGER NOT NULL DEFAULT 0 CHECK (completed IN (0, 1)),
    attempts     INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    completed_at TEXT,
    updated_at   TEXT NOT NULL
);

-- Resultado mais recente de cada exercício de cada lição.
CREATE TABLE course_exercise_results (
    lesson_id   TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    correct     INTEGER NOT NULL CHECK (correct IN (0, 1)),
    last_answer TEXT NOT NULL DEFAULT '',
    attempts    INTEGER NOT NULL DEFAULT 1 CHECK (attempts >= 1),
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (lesson_id, exercise_id)
);
