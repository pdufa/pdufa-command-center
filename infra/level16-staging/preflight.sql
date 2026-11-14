-- Read-only diagnostics. No migrations, source reads, secrets or production writes.
BEGIN READ ONLY;
SELECT current_database() AS database_name,current_user AS effective_role,
       r.rolsuper,r.rolcreaterole,r.rolbypassrls
FROM pg_roles r WHERE r.rolname=current_user;
SELECT n.nspname,c.relname,c.relrowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='level16_review' AND c.relname IN
('events','streams','evidence_bundles','original_documents') ORDER BY c.relname;
SELECT t.tgname,t.tgenabled,c.relname
FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='level16_review' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname;
ROLLBACK;
