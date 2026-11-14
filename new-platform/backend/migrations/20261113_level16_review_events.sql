-- REVIEW ONLY. Apply manually to a disposable test/staging PostgreSQL database.
-- Never run from application startup. No existing tables/history are modified.
-- Migration owner and database superusers remain privileged: retention/backups
-- and separation of DBA duties are required; this is not tamper-proof storage.
BEGIN;
CREATE ROLE pdufa_level16_writer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE SCHEMA level16_review;
REVOKE ALL ON SCHEMA level16_review FROM PUBLIC;
GRANT USAGE ON SCHEMA level16_review TO pdufa_level16_writer;

CREATE TABLE level16_review.reviewer_grants (
    issuer text NOT NULL CHECK (length(issuer) BETWEEN 1 AND 4000),
    subject text NOT NULL CHECK (length(subject) BETWEEN 1 AND 4000),
    role text NOT NULL CHECK (role IN ('SOURCE_VERIFIER','CLINICAL_REVIEWER','INDEPENDENT_CHALLENGER','REVIEW_ADMIN')),
    enabled boolean NOT NULL DEFAULT false,
    PRIMARY KEY (issuer, subject, role)
);
-- Only a separate authorized administrator/DBA may provision/revoke grants.
-- The web runtime may read these grants but cannot modify them.
CREATE TABLE level16_review.streams (
    stream_id uuid PRIMARY KEY,
    binding jsonb NOT NULL CHECK (jsonb_typeof(binding)='object'),
    CHECK (binding->>'nct' ~ '^NCT[0-9]{8}$'),
    CHECK ((binding->>'level')::integer BETWEEN 1 AND 6),
    CHECK (binding->>'documentSha256' ~ '^[0-9a-f]{64}$')
);
-- Stream registrations are immutable and require separately approved evidence
-- registration. The web runtime cannot insert, change or remove bindings.
CREATE TABLE level16_review.events (
    event_id uuid PRIMARY KEY,
    stream_id uuid NOT NULL REFERENCES level16_review.streams(stream_id),
    ordinal integer NOT NULL CHECK (ordinal > 0),
    previous_event_id uuid REFERENCES level16_review.events(event_id),
    event_version integer NOT NULL DEFAULT 1 CHECK (event_version=1),
    reviewer_issuer text NOT NULL,
    reviewer_id text NOT NULL,
    authorized_role text NOT NULL,
    binding jsonb NOT NULL,
    action text NOT NULL CHECK (action IN ('TRANSITION','CORRECTION')),
    status text NOT NULL,
    findings jsonb NOT NULL CHECK (jsonb_typeof(findings)='array' AND jsonb_array_length(findings)>0),
    reasons jsonb NOT NULL CHECK (jsonb_typeof(reasons)='array' AND jsonb_array_length(reasons)>0),
    contradictory_evidence jsonb NOT NULL CHECK (jsonb_typeof(contradictory_evidence)='array'),
    limitations jsonb NOT NULL CHECK (jsonb_typeof(limitations)='array' AND jsonb_array_length(limitations)>0),
    blockers jsonb NOT NULL CHECK (jsonb_typeof(blockers)='array'),
    source_checks jsonb NOT NULL DEFAULT '{}',
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(stream_id, ordinal),
    FOREIGN KEY (reviewer_issuer, reviewer_id, authorized_role)
        REFERENCES level16_review.reviewer_grants(issuer, subject, role)
);

CREATE FUNCTION level16_review.deny_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    RAISE EXCEPTION 'Level 1-6 review history/bindings are append-only; append a correction or new stream';
END $$;
CREATE TRIGGER immutable_events BEFORE UPDATE OR DELETE ON level16_review.events
FOR EACH ROW EXECUTE FUNCTION level16_review.deny_mutation();
CREATE TRIGGER no_truncate_events BEFORE TRUNCATE ON level16_review.events
FOR EACH STATEMENT EXECUTE FUNCTION level16_review.deny_mutation();
CREATE TRIGGER immutable_streams BEFORE UPDATE OR DELETE ON level16_review.streams
FOR EACH ROW EXECUTE FUNCTION level16_review.deny_mutation();
CREATE TRIGGER no_truncate_streams BEFORE TRUNCATE ON level16_review.streams
FOR EACH STATEMENT EXECUTE FUNCTION level16_review.deny_mutation();

CREATE FUNCTION level16_review.protect_grant_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF (NEW.issuer,NEW.subject,NEW.role) IS DISTINCT FROM (OLD.issuer,OLD.subject,OLD.role) THEN
        RAISE EXCEPTION 'Reviewer grant identities/roles cannot be rewritten';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER immutable_grant_identity BEFORE UPDATE ON level16_review.reviewer_grants
FOR EACH ROW EXECUTE FUNCTION level16_review.protect_grant_identity();

CREATE FUNCTION level16_review.check_event() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE
    bundle jsonb;
    prior level16_review.events%ROWTYPE;
    desired_role text;
    stages text[] := ARRAY['SOURCE_SUBMITTED','SOURCE_AUTHENTICATION_PENDING','SOURCE_AUTHENTICATED',
        'SCIENTIFIC_REVIEW_PENDING','SCIENTIFIC_REVIEW_COMPLETED','INDEPENDENT_CHALLENGE_PENDING',
        'INDEPENDENT_CHALLENGE_COMPLETED','FINAL_ADJUDICATION_PENDING','FINAL_ADJUDICATED'];
    exceptional text[] := ARRAY['REJECTED','CONFLICT_UNRESOLVED','ADDITIONAL_EVIDENCE_REQUIRED',
        'SUPERSEDED_BY_NEW_EVIDENCE','NOT_APPLICABLE_AT_CURRENT_PHASE'];
    check_key text;
BEGIN
    -- Lock even an empty stream: two concurrent first events cannot both win.
    SELECT binding INTO STRICT bundle FROM level16_review.streams WHERE stream_id=NEW.stream_id FOR UPDATE;
    IF NEW.binding IS DISTINCT FROM bundle THEN RAISE EXCEPTION 'Stale/cross-identity evidence binding'; END IF;
    SELECT * INTO prior FROM level16_review.events WHERE stream_id=NEW.stream_id ORDER BY ordinal DESC LIMIT 1;
    IF NEW.ordinal <> COALESCE(prior.ordinal,0)+1 OR NEW.previous_event_id IS DISTINCT FROM prior.event_id THEN
        RAISE EXCEPTION 'Conflicting concurrent update or stale predecessor';
    END IF;
    IF NEW.status = ANY(stages[1:3]) THEN desired_role := 'SOURCE_VERIFIER';
    ELSIF NEW.status = ANY(stages[4:5]) THEN desired_role := 'CLINICAL_REVIEWER';
    ELSIF NEW.status = ANY(stages[6:7]) THEN desired_role := 'INDEPENDENT_CHALLENGER';
    ELSIF NEW.status = ANY(stages[8:9]) OR NEW.status = ANY(exceptional) THEN desired_role := 'REVIEW_ADMIN';
    ELSE RAISE EXCEPTION 'Unknown review status'; END IF;
    IF NEW.action = 'CORRECTION' THEN
        IF prior.event_id IS NULL OR NEW.status <> prior.status OR NEW.reviewer_id <> prior.reviewer_id
           OR NEW.reviewer_issuer <> prior.reviewer_issuer THEN RAISE EXCEPTION 'Invalid correction'; END IF;
        desired_role := prior.authorized_role;
    ELSE
        IF prior.action='CORRECTION' THEN
            IF NEW.status <> 'SOURCE_AUTHENTICATION_PENDING' AND NOT NEW.status=ANY(exceptional) THEN
                RAISE EXCEPTION 'Corrected findings require renewed authentication and review'; END IF;
        ELSIF prior.status IN ('FINAL_ADJUDICATED','REJECTED','SUPERSEDED_BY_NEW_EVIDENCE','NOT_APPLICABLE_AT_CURRENT_PHASE') THEN
            IF NEW.status <> 'SUPERSEDED_BY_NEW_EVIDENCE' OR prior.status=NEW.status THEN RAISE EXCEPTION 'Terminal review'; END IF;
        ELSIF NEW.status = ANY(exceptional) THEN
            IF prior.event_id IS NULL THEN RAISE EXCEPTION 'Source submission required'; END IF;
        ELSIF prior.status IN ('CONFLICT_UNRESOLVED','ADDITIONAL_EVIDENCE_REQUIRED') THEN
            IF NEW.status <> 'SOURCE_AUTHENTICATION_PENDING' THEN RAISE EXCEPTION 'Repeat authentication required'; END IF;
        ELSIF NEW.status IS DISTINCT FROM stages[COALESCE(array_position(stages,prior.status),0)+1] THEN
            RAISE EXCEPTION 'Required stages cannot be skipped';
        END IF;
    END IF;
    IF NEW.authorized_role <> desired_role OR NOT EXISTS (
        SELECT 1 FROM level16_review.reviewer_grants WHERE issuer=NEW.reviewer_issuer
        AND subject=NEW.reviewer_id AND role=desired_role AND enabled) THEN RAISE EXCEPTION 'Reviewer not authorized'; END IF;
    -- Lock grants against concurrent administrative revocation until commit.
    PERFORM 1 FROM level16_review.reviewer_grants WHERE issuer=NEW.reviewer_issuer
        AND subject=NEW.reviewer_id AND role=desired_role AND enabled FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Reviewer grant revoked'; END IF;
    IF NEW.status='SOURCE_AUTHENTICATED' AND EXISTS (
        SELECT 1 FROM level16_review.events WHERE stream_id=NEW.stream_id
        AND reviewer_id=NEW.reviewer_id AND reviewer_issuer=NEW.reviewer_issuer
        AND status='SOURCE_SUBMITTED') THEN RAISE EXCEPTION 'Source self authentication prohibited'; END IF;
    IF desired_role='CLINICAL_REVIEWER' AND EXISTS (
        SELECT 1 FROM level16_review.events WHERE stream_id=NEW.stream_id
        AND reviewer_id=NEW.reviewer_id AND reviewer_issuer=NEW.reviewer_issuer
        AND authorized_role='SOURCE_VERIFIER') THEN RAISE EXCEPTION 'Source participant self review prohibited'; END IF;
    IF desired_role='INDEPENDENT_CHALLENGER'  AND EXISTS (
        SELECT 1 FROM level16_review.events WHERE stream_id=NEW.stream_id
        AND reviewer_id=NEW.reviewer_id AND reviewer_issuer=NEW.reviewer_issuer
        AND authorized_role IN ('SOURCE_VERIFIER','CLINICAL_REVIEWER')) THEN RAISE EXCEPTION 'Self challenge prohibited'; END IF;
    IF NEW.status IN ('FINAL_ADJUDICATION_PENDING','FINAL_ADJUDICATED') AND EXISTS (
        SELECT 1 FROM level16_review.events WHERE stream_id=NEW.stream_id
        AND reviewer_id=NEW.reviewer_id AND reviewer_issuer=NEW.reviewer_issuer
        AND authorized_role <> 'REVIEW_ADMIN') THEN RAISE EXCEPTION 'Self adjudication prohibited'; END IF;
    IF NEW.status='NOT_APPLICABLE_AT_CURRENT_PHASE' AND (
        (bundle->>'level')::integer NOT IN (3,5) OR jsonb_array_length(bundle->'phases')=0 OR EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(bundle->'phases') AS p(value)
            WHERE value NOT IN ('EARLY_PHASE1','PHASE1','PHASE2'))) THEN RAISE EXCEPTION 'Invalid phase waiver'; END IF;
    IF NEW.status='CONFLICT_UNRESOLVED' AND jsonb_array_length(NEW.contradictory_evidence)=0 THEN
        RAISE EXCEPTION 'Contradictory evidence required'; END IF;
    IF NEW.status IN ('SCIENTIFIC_REVIEW_COMPLETED','INDEPENDENT_CHALLENGE_COMPLETED','FINAL_ADJUDICATED')
       AND (jsonb_array_length(NEW.blockers)>0 OR jsonb_array_length(NEW.contradictory_evidence)>0) THEN
        RAISE EXCEPTION 'Unresolved blockers/contradictions prevent completion'; END IF;
    IF NEW.status='SOURCE_AUTHENTICATED' THEN
        FOREACH check_key IN ARRAY ARRAY['exactNct','phase','registryStatus','indication','population',
            'sourceOwnership','publicationDate','retrievalDate','originalDocument','documentVersion',
            'protocolVersion','cutoff','conflicts'] LOOP
            IF NEW.source_checks->check_key IS DISTINCT FROM 'true'::jsonb THEN
                RAISE EXCEPTION 'Independent original-source check missing: %', check_key;
            END IF;
        END LOOP;
    ELSIF NEW.source_checks <> '{}'::jsonb THEN RAISE EXCEPTION 'Source checks belong only to authentication event'; END IF;
    NEW.recorded_at := clock_timestamp(); -- caller cannot choose review time
    NEW.event_version := 1;
    RETURN NEW;
END $$;
CREATE TRIGGER verify_event BEFORE INSERT ON level16_review.events
FOR EACH ROW EXECUTE FUNCTION level16_review.check_event();
REVOKE ALL ON ALL TABLES IN SCHEMA level16_review FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA level16_review FROM PUBLIC;
GRANT SELECT ON level16_review.streams, level16_review.events, level16_review.reviewer_grants TO pdufa_level16_writer;
-- Required for SELECT FOR UPDATE / FOR SHARE, but mutation is blocked by
-- triggers for streams and by restricted column grants for reviewer grants.
GRANT UPDATE(stream_id) ON level16_review.streams TO pdufa_level16_writer;
-- Grant locking rights on the immutable PK column only; enabled/role cannot change.
GRANT UPDATE(issuer) ON level16_review.reviewer_grants TO pdufa_level16_writer;
GRANT INSERT ON level16_review.events TO pdufa_level16_writer;
COMMIT;
