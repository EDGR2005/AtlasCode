-- Sample SQL schema for CodeAtlas DB analyzer tests

CREATE TABLE users (
    id          INTEGER     NOT NULL PRIMARY KEY,
    username    VARCHAR(64) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    created_at  DATETIME    NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT 1
);

CREATE TABLE posts (
    id          INTEGER     NOT NULL PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    body        TEXT,
    author_id   INTEGER     NOT NULL REFERENCES users(id),
    created_at  DATETIME    NOT NULL
);

CREATE TABLE comments (
    id          INTEGER     NOT NULL PRIMARY KEY,
    body        TEXT        NOT NULL,
    post_id     INTEGER     NOT NULL,
    author_id   INTEGER     NOT NULL,
    created_at  DATETIME    NOT NULL,
    FOREIGN KEY (post_id)   REFERENCES posts(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE tags (
    id    INTEGER     NOT NULL PRIMARY KEY,
    name  VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE post_tags (
    post_id  INTEGER NOT NULL REFERENCES posts(id),
    tag_id   INTEGER NOT NULL REFERENCES tags(id),
    PRIMARY KEY (post_id, tag_id)
);
