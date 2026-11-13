-- Additive, REVIEW ONLY. Depends on 20261113_level16_review_events.sql.
-- Apply only to an explicitly isolated staging/disposable test database.
-- No application startup migration and no production configuration changes.
BEGIN;
CREATE TABLE level16_review.identity_accounts (
    token_issuer text NOT NULL, token_subject text NOT NULL, person_id uuid NOT NULL,
    PRIMARY KEY(token_issuer,token_subject)
);
CREATE TABLE level16_review.identity_sessions (
    token_issuer text NOT NULL, session_id text NOT NULL, token_subject text NOT NULL,
    valid_after timestamptz NOT NULL, expires_at timestamptz NOT NULL, revoked_at timestamptz,
    PRIMARY KEY(token_issuer,session_id),
    FOREIGN KEY(token_issuer,token_subject) REFERENCES level16_review.identity_accounts,
    CHECK(expires_at>valid_after)
);
CREATE TABLE level16_review.revoked_tokens (
    token_issuer text NOT NULL, token_id text NOT NULL, session_id text NOT NULL, recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(token_issuer,token_id),
    FOREIGN KEY(token_issuer,session_id) REFERENCES level16_review.identity_sessions
);
CREATE TABLE level16_review.authorization_audit (
    audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    decision text NOT NULL CHECK(decision IN ('AUTHENTICATED','AUTHORIZED','DENIED')),
    reason text NOT NULL CHECK(reason IN ('TOKEN_VALID','TOKEN_REJECTED','SESSION_REJECTED','ROLE_REJECTED','ACCESS_VALID','REVIEW_APPEND_REJECTED')),
    token_issuer text, reviewer_id text
);
CREATE TABLE level16_review.original_documents (
    document_id text PRIMARY KEY, sha256 text NOT NULL CHECK(sha256 ~ '^[0-9a-f]{64}$'),
    original_bytes bytea CHECK(octet_length(original_bytes)<=67108864)
);
CREATE TABLE level16_review.evidence_bundles (
    stream_id uuid PRIMARY KEY REFERENCES level16_review.streams,
    manifest jsonb NOT NULL, document_ids text[] NOT NULL,
    signed_attestation text NOT NULL CHECK(length(signed_attestation)<=32768)
);
CREATE TABLE level16_review.evidence_access (
    issuer text NOT NULL, subject text NOT NULL, stream_id uuid NOT NULL REFERENCES level16_review.streams,
    enabled boolean NOT NULL DEFAULT false, PRIMARY KEY(issuer,subject,stream_id)
);
CREATE TABLE level16_review.current_evidence_versions (
    nct text NOT NULL CHECK(nct ~ '^NCT[0-9]{8}$'), level integer NOT NULL CHECK(level BETWEEN 1 AND 6),
    stream_id uuid NOT NULL REFERENCES level16_review.evidence_bundles,
    generation integer NOT NULL CHECK(generation>0), PRIMARY KEY(nct,level)
);

CREATE FUNCTION level16_review.staging_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Immutable staging evidence, identity association or audit history'; END $$;
DO $$ DECLARE tab text; BEGIN
    FOREACH tab IN ARRAY ARRAY['identity_accounts','revoked_tokens','authorization_audit','original_documents','evidence_bundles'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_staging_row BEFORE UPDATE OR DELETE ON level16_review.%I FOR EACH ROW EXECUTE FUNCTION level16_review.staging_immutable()',tab);
        EXECUTE format('CREATE TRIGGER no_truncate_staging BEFORE TRUNCATE ON level16_review.%I FOR EACH STATEMENT EXECUTE FUNCTION level16_review.staging_immutable()',tab);
    END LOOP;
END $$;
CREATE FUNCTION level16_review.staging_keys() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF TG_TABLE_NAME='identity_sessions' THEN
        IF (NEW.token_issuer,NEW.session_id,NEW.token_subject) IS DISTINCT FROM (OLD.token_issuer,OLD.session_id,OLD.token_subject) THEN
            RAISE EXCEPTION 'Session identity cannot be rewritten'; END IF;
    ELSIF TG_TABLE_NAME='evidence_access' THEN
        IF (NEW.issuer,NEW.subject,NEW.stream_id) IS DISTINCT FROM (OLD.issuer,OLD.subject,OLD.stream_id) THEN
            RAISE EXCEPTION 'Evidence access identity cannot be rewritten'; END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER protect_session_keys BEFORE UPDATE ON level16_review.identity_sessions
FOR EACH ROW EXECUTE FUNCTION level16_review.staging_keys();
CREATE TRIGGER protect_access_keys BEFORE UPDATE ON level16_review.evidence_access
FOR EACH ROW EXECUTE FUNCTION level16_review.staging_keys();
CREATE FUNCTION level16_review.current_version_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE b jsonb; prior jsonb;
BEGIN
    SELECT binding INTO STRICT b FROM level16_review.streams WHERE stream_id=NEW.stream_id;
    IF b->>'nct' <> NEW.nct OR (b->>'level')::integer <> NEW.level THEN RAISE EXCEPTION 'Cross-trial/level source index'; END IF;
    IF TG_OP='UPDATE' THEN
        IF (NEW.nct,NEW.level) IS DISTINCT FROM (OLD.nct,OLD.level) THEN RAISE EXCEPTION 'Source index key immutable'; END IF;
        IF NEW.stream_id=OLD.stream_id AND NEW.generation=OLD.generation THEN RETURN NEW; END IF;
        SELECT binding INTO STRICT prior FROM level16_review.streams WHERE stream_id=OLD.stream_id;
        IF NEW.generation<>OLD.generation+1 OR (b->>'evidenceVersion')::integer <= (prior->>'evidenceVersion')::integer THEN
            RAISE EXCEPTION 'Current evidence versions must advance monotonically'; END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER protect_current_version BEFORE INSERT OR UPDATE ON level16_review.current_evidence_versions
FOR EACH ROW EXECUTE FUNCTION level16_review.current_version_guard();
CREATE TRIGGER no_delete_current_version BEFORE DELETE ON level16_review.current_evidence_versions
FOR EACH ROW EXECUTE FUNCTION level16_review.staging_immutable();
CREATE TRIGGER no_truncate_current_version BEFORE TRUNCATE ON level16_review.current_evidence_versions
FOR EACH STATEMENT EXECUTE FUNCTION level16_review.staging_immutable();
CREATE FUNCTION level16_review.serialize_token_revocation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    PERFORM 1 FROM level16_review.identity_sessions WHERE token_issuer=NEW.token_issuer AND session_id=NEW.session_id FOR UPDATE;
    RETURN NEW;
END $$;
CREATE TRIGGER lock_revoked_session BEFORE INSERT ON level16_review.revoked_tokens
FOR EACH ROW EXECUTE FUNCTION level16_review.serialize_token_revocation();
CREATE FUNCTION level16_review.audit_server_time() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN NEW.recorded_at:=clock_timestamp(); RETURN NEW; END $$;
CREATE TRIGGER authorization_server_time BEFORE INSERT ON level16_review.authorization_audit
FOR EACH ROW EXECUTE FUNCTION level16_review.audit_server_time();

-- The runtime sets this context only after signature and session validation.
-- Direct database credentials remain a trusted server boundary, never a client credential.
CREATE FUNCTION level16_review.staging_session_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE person uuid;
BEGIN
    SELECT a.person_id INTO person FROM level16_review.identity_sessions s
    JOIN level16_review.identity_accounts a ON (a.token_issuer,a.token_subject)=(s.token_issuer,s.token_subject)
    WHERE s.token_issuer=current_setting('level16.token_issuer',true)
      AND s.token_subject=current_setting('level16.token_subject',true)
      AND s.session_id=current_setting('level16.session_id',true)
      AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
      AND to_timestamp(current_setting('level16.issued_at',true)::double precision)>=s.valid_after
      AND to_timestamp(current_setting('level16.expires_at',true)::double precision)<=s.expires_at
      AND to_timestamp(current_setting('level16.expires_at',true)::double precision)>clock_timestamp()
      AND NOT EXISTS (SELECT 1 FROM level16_review.revoked_tokens r
          WHERE r.token_issuer=s.token_issuer AND r.token_id=current_setting('level16.token_id',true)) FOR SHARE OF s;
    IF person IS NULL OR NEW.reviewer_issuer<>'level16-approved-person'
       OR NEW.reviewer_id<>person::text THEN RAISE EXCEPTION 'Verified reviewer session required'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER require_staging_session BEFORE INSERT ON level16_review.events
FOR EACH ROW EXECUTE FUNCTION level16_review.staging_session_guard();

REVOKE ALL ON ALL TABLES IN SCHEMA level16_review FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA level16_review FROM PUBLIC;
GRANT SELECT ON level16_review.identity_accounts,level16_review.identity_sessions,
    level16_review.revoked_tokens,level16_review.evidence_access,level16_review.current_evidence_versions,
    level16_review.original_documents,level16_review.evidence_bundles TO pdufa_level16_writer;
GRANT INSERT ON level16_review.authorization_audit TO pdufa_level16_writer;
-- Column grants enable row locks only; immutable/key guards prevent rewrites.
GRANT UPDATE(token_issuer) ON level16_review.identity_sessions TO pdufa_level16_writer;
GRANT UPDATE(issuer) ON level16_review.evidence_access TO pdufa_level16_writer;
GRANT UPDATE(nct) ON level16_review.current_evidence_versions TO pdufa_level16_writer;
GRANT UPDATE(document_id) ON level16_review.original_documents TO pdufa_level16_writer;
GRANT UPDATE(stream_id) ON level16_review.evidence_bundles TO pdufa_level16_writer;

-- Evidence/history access is also constrained in PostgreSQL, not just in HTML.
ALTER TABLE level16_review.streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE level16_review.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE level16_review.evidence_bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE level16_review.original_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY stream_access ON level16_review.streams TO pdufa_level16_writer USING (
    EXISTS (SELECT 1 FROM level16_review.evidence_access a WHERE a.stream_id=streams.stream_id AND a.enabled
        AND a.issuer=current_setting('level16.issuer',true) AND a.subject=current_setting('level16.subject',true)));
CREATE POLICY event_access ON level16_review.events TO pdufa_level16_writer USING (
    EXISTS (SELECT 1 FROM level16_review.evidence_access a WHERE a.stream_id=events.stream_id AND a.enabled
        AND a.issuer=current_setting('level16.issuer',true) AND a.subject=current_setting('level16.subject',true)));
CREATE POLICY bundle_access ON level16_review.evidence_bundles TO pdufa_level16_writer USING (
    EXISTS (SELECT 1 FROM level16_review.evidence_access a WHERE a.stream_id=evidence_bundles.stream_id AND a.enabled
        AND a.issuer=current_setting('level16.issuer',true) AND a.subject=current_setting('level16.subject',true)));
CREATE POLICY document_access ON level16_review.original_documents TO pdufa_level16_writer USING (
    EXISTS (SELECT 1 FROM level16_review.evidence_bundles b WHERE original_documents.document_id=ANY(b.document_ids)));
COMMIT;
