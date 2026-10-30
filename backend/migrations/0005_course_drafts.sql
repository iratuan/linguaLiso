-- Lições geradas pelo modelo que ainda aguardam revisão do usuário.
-- Só depois de aprovadas viram parte da trilha (arquivo em <dados>/curriculo_usuario).

CREATE TABLE course_lesson_drafts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    language    TEXT NOT NULL,
    level       TEXT NOT NULL,
    title       TEXT NOT NULL,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_course_drafts_language_level ON course_lesson_drafts (language, level);
