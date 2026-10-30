-- Análises de nível feitas pelo professor sobre uma conversa encerrada.
-- O resultado completo fica em JSON; as colunas principais servem para listar sem abrir cada análise.

CREATE TABLE level_analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    model           TEXT NOT NULL,
    declared_level  TEXT NOT NULL,
    level_estimate  TEXT NOT NULL,
    confidence      TEXT NOT NULL,
    student_turns   INTEGER NOT NULL,
    payload         TEXT NOT NULL
);

CREATE INDEX idx_level_analyses_session ON level_analyses (session_id);
