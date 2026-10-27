DROP TABLE IF EXISTS articles;

CREATE TABLE articles (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        TEXT,
    description  TEXT,
    published_at TIMESTAMPTZ,
    author_name  TEXT,
    content      TEXT,
    url          TEXT NOT NULL UNIQUE,
    source       TEXT NOT NULL
);