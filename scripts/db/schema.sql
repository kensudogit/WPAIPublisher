-- WPAIPublisher sessions (Railway Postgres / local)
CREATE TABLE IF NOT EXISTS sessions (
  id            TEXT PRIMARY KEY,
  status        TEXT NOT NULL DEFAULT 'unknown',
  agent         TEXT NOT NULL DEFAULT '-',
  target        TEXT NOT NULL DEFAULT '?',
  staging_url   TEXT,
  production_url TEXT,
  notes         TEXT,
  manifest      JSONB,
  task          JSONB,
  created_at    TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sessions_updated_at_idx ON sessions (updated_at DESC);
CREATE INDEX IF NOT EXISTS sessions_status_idx ON sessions (status);
