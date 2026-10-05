CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS columns (
    board_id INTEGER NOT NULL,
    id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 80),
    position INTEGER NOT NULL,
    PRIMARY KEY (board_id, id),
    UNIQUE (board_id, position),
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
    CHECK ((id = 'col-backlog' AND position = 0) OR (id = 'col-discovery' AND position = 1) OR (id = 'col-progress' AND position = 2) OR (id = 'col-review' AND position = 3) OR (id = 'col-done' AND position = 4))
);

CREATE TABLE IF NOT EXISTS cards (
    id TEXT NOT NULL PRIMARY KEY,
    board_id INTEGER NOT NULL,
    column_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    details TEXT NOT NULL DEFAULT '' CHECK (length(details) <= 10000),
    position INTEGER NOT NULL CHECK (position >= 0),
    FOREIGN KEY (board_id, column_id) REFERENCES columns(board_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS cards_board_column_position ON cards (board_id, column_id, position);
