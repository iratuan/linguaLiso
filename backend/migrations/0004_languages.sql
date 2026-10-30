-- Suporte a mais de um idioma-alvo.
-- Dados existentes ficam como inglês ('en'), que é o idioma original do aplicativo.

ALTER TABLE conversation_sessions ADD COLUMN language TEXT NOT NULL DEFAULT 'en';

-- O vocabulário passa a ser único por idioma: "chat" (inglês) e "chat" (francês) podem coexistir.
-- Reconstrução da tabela; as chaves estrangeiras ficam desligadas durante a migração (ver db.py).
CREATE TABLE vocabulary_items_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    language          TEXT NOT NULL DEFAULT 'en',
    term              TEXT NOT NULL,
    translation_pt    TEXT NOT NULL DEFAULT '',
    example_sentence  TEXT NOT NULL DEFAULT '',
    source_session_id INTEGER REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    box               INTEGER NOT NULL DEFAULT 0 CHECK (box BETWEEN 0 AND 5),
    next_review_at    TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    UNIQUE (language, term COLLATE NOCASE)
);

INSERT INTO vocabulary_items_new
    (id, language, term, translation_pt, example_sentence, source_session_id, box, next_review_at, created_at)
SELECT id, 'en', term, translation_pt, example_sentence, source_session_id, box, next_review_at, created_at
FROM vocabulary_items;

DROP TABLE vocabulary_items;
ALTER TABLE vocabulary_items_new RENAME TO vocabulary_items;
CREATE INDEX idx_vocab_next_review ON vocabulary_items(next_review_at);
