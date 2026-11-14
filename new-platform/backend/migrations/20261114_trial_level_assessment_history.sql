-- Additive only. Existing assessment and prediction archives are untouched.
CREATE TABLE IF NOT EXISTS level_assessment_runs (
    run_id VARCHAR(36) PRIMARY KEY,
    nct_id VARCHAR(11) NOT NULL,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 6),
    engine_version VARCHAR(80) NOT NULL,
    evidence_hash VARCHAR(64) NOT NULL,
    report JSON NOT NULL,
    saved_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_level_assessment_runs_nct_id ON level_assessment_runs(nct_id);
