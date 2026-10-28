DROP TABLE IF EXISTS articles_clean;

CREATE TABLE articles_clean (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        TEXT,
    description  TEXT,
    published_at TIMESTAMPTZ,
    author_name  TEXT,
    content      TEXT,
    url          TEXT NOT NULL UNIQUE,
    source       TEXT NOT NULL
);