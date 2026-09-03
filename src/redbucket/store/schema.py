"""权威 DDL，与 schema-sqlite.md Full SQL DDL 一致。"""
from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version     INTEGER PRIMARY KEY,
  applied_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id                   INTEGER PRIMARY KEY,
  username             TEXT    NOT NULL,
  username_normalized  TEXT    NOT NULL,
  email                TEXT    NOT NULL,
  email_normalized     TEXT    NOT NULL,
  password_hash        TEXT    NOT NULL,
  bucket_quota         INTEGER NOT NULL DEFAULT 5,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  CONSTRAINT users_username_normalized_uq UNIQUE (username_normalized),
  CONSTRAINT users_email_normalized_uq UNIQUE (email_normalized),
  CONSTRAINT users_bucket_quota_ck CHECK (bucket_quota >= 0)
);

CREATE TABLE IF NOT EXISTS tokens (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL,
  token_hash   TEXT    NOT NULL,
  created_at   TEXT    NOT NULL,
  last_used_at TEXT    NOT NULL,
  revoked_at   TEXT,
  CONSTRAINT tokens_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT tokens_token_hash_uq UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS tokens_user_id_idx ON tokens(user_id);
CREATE INDEX IF NOT EXISTS tokens_active_idx
  ON tokens(user_id, revoked_at);

CREATE TABLE IF NOT EXISTS buckets (
  id                   INTEGER PRIMARY KEY,
  user_id              INTEGER NOT NULL,
  name                 TEXT    NOT NULL,
  name_normalized      TEXT    NOT NULL,
  visibility           TEXT    NOT NULL DEFAULT 'private',
  description          TEXT    NOT NULL DEFAULT '',
  template             TEXT,
  storage_usage_bytes  INTEGER NOT NULL DEFAULT 0,
  storage_limit_bytes  INTEGER NOT NULL DEFAULT 10485760,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  deleted_at           TEXT,
  CONSTRAINT buckets_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT buckets_visibility_ck
    CHECK (visibility IN ('public', 'private')),
  CONSTRAINT buckets_template_ck
    CHECK (
      template IS NULL
      OR template IN ('codex', 'agents', 'claude', 'openclaw')
    ),
  CONSTRAINT buckets_description_len_ck
    CHECK (length(description) <= 350),
  CONSTRAINT buckets_usage_ck CHECK (storage_usage_bytes >= 0),
  CONSTRAINT buckets_limit_ck CHECK (storage_limit_bytes > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS buckets_user_name_live_uq
  ON buckets(user_id, name_normalized)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS buckets_user_id_idx ON buckets(user_id);
CREATE INDEX IF NOT EXISTS buckets_user_visibility_idx
  ON buckets(user_id, visibility)
  WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS assets (
  id               INTEGER PRIMARY KEY,
  bucket_id        INTEGER NOT NULL,
  type             TEXT    NOT NULL,
  source_harness   TEXT    NOT NULL,
  path             TEXT    NOT NULL,
  size_bytes       INTEGER NOT NULL,
  uploader_id      INTEGER NOT NULL,
  source_copy_id   INTEGER,
  head_commit_sha  TEXT    NOT NULL,
  created_at       TEXT    NOT NULL,
  updated_at       TEXT    NOT NULL,
  CONSTRAINT assets_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT assets_uploader_fk
    FOREIGN KEY (uploader_id) REFERENCES users(id),
  CONSTRAINT assets_type_ck
    CHECK (
      type IN (
        'skill', 'mcp', 'instructions', 'subagent', 'plugin'
      )
    ),
  CONSTRAINT assets_harness_ck
    CHECK (
      source_harness IN (
        'codex', 'agents', 'claude', 'openclaw'
      )
    ),
  CONSTRAINT assets_size_ck CHECK (size_bytes >= 0),
  CONSTRAINT assets_bucket_path_uq UNIQUE (bucket_id, path)
);

CREATE INDEX IF NOT EXISTS assets_bucket_id_idx ON assets(bucket_id);
CREATE INDEX IF NOT EXISTS assets_bucket_type_idx
  ON assets(bucket_id, type);
CREATE INDEX IF NOT EXISTS assets_uploader_id_idx ON assets(uploader_id);

CREATE TABLE IF NOT EXISTS copies (
  id                 INTEGER PRIMARY KEY,
  dest_bucket_id     INTEGER NOT NULL,
  dest_asset_id      INTEGER,
  dest_path          TEXT    NOT NULL,
  dest_type          TEXT    NOT NULL,
  source_bucket_id   INTEGER NOT NULL,
  source_full_name   TEXT    NOT NULL,
  source_path        TEXT    NOT NULL,
  source_commit_sha  TEXT    NOT NULL,
  dest_commit_sha    TEXT    NOT NULL,
  actor_id           INTEGER NOT NULL,
  created_at         TEXT    NOT NULL,
  CONSTRAINT copies_dest_bucket_fk
    FOREIGN KEY (dest_bucket_id) REFERENCES buckets(id),
  CONSTRAINT copies_dest_asset_fk
    FOREIGN KEY (dest_asset_id) REFERENCES assets(id)
    ON DELETE SET NULL,
  CONSTRAINT copies_actor_fk
    FOREIGN KEY (actor_id) REFERENCES users(id),
  CONSTRAINT copies_dest_type_ck
    CHECK (
      dest_type IN (
        'skill', 'mcp', 'instructions', 'subagent', 'plugin'
      )
    )
);

CREATE INDEX IF NOT EXISTS copies_dest_bucket_id_idx
  ON copies(dest_bucket_id);
CREATE INDEX IF NOT EXISTS copies_dest_asset_id_idx
  ON copies(dest_asset_id);
CREATE INDEX IF NOT EXISTS copies_actor_id_idx ON copies(actor_id);

CREATE TABLE IF NOT EXISTS issues (
  id           INTEGER PRIMARY KEY,
  bucket_id    INTEGER NOT NULL,
  number       INTEGER NOT NULL,
  author_id    INTEGER NOT NULL,
  title        TEXT    NOT NULL,
  body         TEXT    NOT NULL DEFAULT '',
  state        TEXT    NOT NULL DEFAULT 'open',
  closed_by_id INTEGER,
  created_at   TEXT    NOT NULL,
  updated_at   TEXT    NOT NULL,
  closed_at    TEXT,
  CONSTRAINT issues_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT issues_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT issues_closed_by_fk
    FOREIGN KEY (closed_by_id) REFERENCES users(id),
  CONSTRAINT issues_state_ck CHECK (state IN ('open', 'closed')),
  CONSTRAINT issues_number_ck CHECK (number >= 1),
  CONSTRAINT issues_bucket_number_uq UNIQUE (bucket_id, number)
);

CREATE INDEX IF NOT EXISTS issues_bucket_state_idx
  ON issues(bucket_id, state);
CREATE INDEX IF NOT EXISTS issues_author_id_idx ON issues(author_id);

CREATE TABLE IF NOT EXISTS issue_comments (
  id         INTEGER PRIMARY KEY,
  issue_id   INTEGER NOT NULL,
  author_id  INTEGER NOT NULL,
  body       TEXT    NOT NULL,
  created_at TEXT    NOT NULL,
  updated_at TEXT    NOT NULL,
  CONSTRAINT issue_comments_issue_fk
    FOREIGN KEY (issue_id) REFERENCES issues(id),
  CONSTRAINT issue_comments_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT issue_comments_body_ck CHECK (length(body) > 0)
);

CREATE INDEX IF NOT EXISTS issue_comments_issue_id_idx
  ON issue_comments(issue_id);
CREATE INDEX IF NOT EXISTS issue_comments_author_id_idx
  ON issue_comments(author_id);

CREATE TABLE IF NOT EXISTS pull_requests (
  id                   INTEGER PRIMARY KEY,
  bucket_id            INTEGER NOT NULL,
  number               INTEGER NOT NULL,
  author_id            INTEGER NOT NULL,
  title                TEXT    NOT NULL,
  body                 TEXT    NOT NULL DEFAULT '',
  state                TEXT    NOT NULL DEFAULT 'open',
  proposed_files_json  TEXT    NOT NULL,
  merged_commit_sha    TEXT,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  closed_at            TEXT,
  CONSTRAINT pull_requests_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT pull_requests_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT pull_requests_state_ck
    CHECK (state IN ('open', 'merged', 'rejected')),
  CONSTRAINT pull_requests_number_ck CHECK (number >= 1),
  CONSTRAINT pull_requests_bucket_number_uq UNIQUE (bucket_id, number)
);

CREATE INDEX IF NOT EXISTS pull_requests_bucket_state_idx
  ON pull_requests(bucket_id, state);
CREATE INDEX IF NOT EXISTS pull_requests_author_id_idx
  ON pull_requests(author_id);

CREATE TABLE IF NOT EXISTS device_codes (
  id                INTEGER PRIMARY KEY,
  device_code_hash  TEXT    NOT NULL,
  user_code         TEXT    NOT NULL,
  client            TEXT    NOT NULL DEFAULT '',
  state             TEXT    NOT NULL DEFAULT 'pending',
  user_id           INTEGER,
  created_at        TEXT    NOT NULL,
  expires_at        TEXT    NOT NULL,
  CONSTRAINT device_codes_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT device_codes_state_ck
    CHECK (state IN ('pending', 'approved', 'denied', 'collected')),
  CONSTRAINT device_codes_hash_uq UNIQUE (device_code_hash),
  CONSTRAINT device_codes_user_code_uq UNIQUE (user_code)
);

CREATE INDEX IF NOT EXISTS device_codes_user_code_idx
  ON device_codes(user_code);
"""
