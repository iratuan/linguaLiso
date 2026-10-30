-- Histórico completo de tentativas nos exercícios do curso.
-- Diferente de course_exercise_results (só a última resposta), aqui fica cada verificação,
-- o que permite desenhar a evolução do aluno ao longo do tempo.

CREATE TABLE course_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id   TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    correct     INTEGER NOT NULL CHECK (correct IN (0, 1)),
    answer      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_course_attempts_time ON course_attempts(created_at);
