-- Esquema inicial do English Teacher Local.
-- Datas sempre em UTC, ISO 8601 (TEXT).

CREATE TABLE app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE learner_profile (
    id                   INTEGER PRIMARY KEY CHECK (id = 1),
    display_name         TEXT NOT NULL DEFAULT '',
    level                TEXT NOT NULL DEFAULT 'A1'
                         CHECK (level IN ('A1', 'A2', 'B1', 'B2', 'C1')),
    english_variant      TEXT NOT NULL DEFAULT 'american'
                         CHECK (english_variant IN ('american', 'british')),
    explanation_language TEXT NOT NULL DEFAULT 'pt-BR',
    study_minutes_goal   INTEGER NOT NULL DEFAULT 20 CHECK (study_minutes_goal BETWEEN 5 AND 240),
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE learning_goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'done', 'archived')),
    created_at  TEXT NOT NULL
);

CREATE TABLE lessons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    objective    TEXT NOT NULL,
    content_md   TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'completed')),
    summary      TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE lesson_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL CHECK (position >= 1),
    prompt          TEXT NOT NULL,
    expected_answer TEXT NOT NULL DEFAULT '',
    user_answer     TEXT,
    is_correct      INTEGER CHECK (is_correct IN (0, 1)),
    feedback        TEXT NOT NULL DEFAULT '',
    answered_at     TEXT,
    UNIQUE (lesson_id, position)
);

CREATE TABLE conversation_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    mode       TEXT NOT NULL CHECK (mode IN (
                   'free', 'guided_lesson', 'grammar', 'vocabulary',
                   'roleplay', 'error_review', 'listening')),
    scenario   TEXT,
    title      TEXT NOT NULL DEFAULT '',
    level      TEXT NOT NULL CHECK (level IN ('A1', 'A2', 'B1', 'B2', 'C1')),
    model      TEXT NOT NULL,
    lesson_id  INTEGER REFERENCES lessons(id) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at   TEXT
);
CREATE INDEX idx_sessions_started ON conversation_sessions(started_at DESC);

CREATE TABLE messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role         TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content      TEXT NOT NULL,
    input_source TEXT NOT NULL DEFAULT 'text' CHECK (input_source IN ('text', 'voice')),
    created_at   TEXT NOT NULL
);
CREATE INDEX idx_messages_session ON messages(session_id, id);

CREATE TABLE corrections (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id     INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    session_id     INTEGER NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    original_text  TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    explanation_pt TEXT NOT NULL DEFAULT '',
    error_category TEXT NOT NULL CHECK (error_category IN (
                       'grammar', 'vocabulary', 'context', 'spelling', 'other')),
    severity       TEXT NOT NULL CHECK (severity IN ('minor', 'moderate', 'major')),
    example_sentence TEXT NOT NULL DEFAULT '',
    practice_prompt  TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL
);
CREATE INDEX idx_corrections_category ON corrections(error_category);
CREATE INDEX idx_corrections_message ON corrections(message_id);

CREATE TABLE vocabulary_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    term              TEXT NOT NULL,
    translation_pt    TEXT NOT NULL DEFAULT '',
    example_sentence  TEXT NOT NULL DEFAULT '',
    source_session_id INTEGER REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    box               INTEGER NOT NULL DEFAULT 0 CHECK (box BETWEEN 0 AND 5),
    next_review_at    TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    UNIQUE (term COLLATE NOCASE)
);
CREATE INDEX idx_vocab_next_review ON vocabulary_items(next_review_at);

CREATE TABLE vocabulary_reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES vocabulary_items(id) ON DELETE CASCADE,
    rating      TEXT NOT NULL CHECK (rating IN ('forgot', 'hard', 'good')),
    box_before  INTEGER NOT NULL,
    box_after   INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE INDEX idx_vocab_reviews_item ON vocabulary_reviews(item_id);
