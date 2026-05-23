-- Run this in the Supabase SQL Editor to create all tables.

CREATE TABLE exercises (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  muscle_group TEXT,
  category     TEXT
);

CREATE TABLE sessions (
  id        SERIAL PRIMARY KEY,
  date      DATE NOT NULL DEFAULT CURRENT_DATE,
  day_type  TEXT,
  notes     TEXT
);

CREATE TABLE sets (
  id          SERIAL PRIMARY KEY,
  session_id  INT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  exercise_id INT NOT NULL REFERENCES exercises(id),
  set_number  INT NOT NULL,
  weight_kg   NUMERIC(6, 2),
  reps        INT,
  rir         INT,
  logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX idx_sets_session    ON sets(session_id);
CREATE INDEX idx_sets_exercise   ON sets(exercise_id);
CREATE INDEX idx_sets_logged_at  ON sets(logged_at DESC);
