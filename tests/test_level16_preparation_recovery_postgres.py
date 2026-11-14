"""Actual pg_dump/pg_restore drill on newly created synthetic test databases only."""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
import test_level16_review_postgres as prior
from test_level16_review_events import ROOT
from app.level16_review_events import ReviewEventService


@unittest.skipUnless(os.getenv('LEVEL16_TEST_ALLOW_DISPOSABLE')=='1'
    and os.getenv('LEVEL16_TEST_DATABASE_URL') and os.getenv('LEVEL16_TEST_POSTGRES_CONTAINER_ID'),
    'Explicit disposable PostgreSQL container required for actual restore drill')
class PreparationRecoveryTests(unittest.TestCase):
    cleanup=classmethod(prior.ReviewPostgresTests.cleanup.__func__)

    @classmethod
    def setUpClass(cls):
        prior.ReviewPostgresTests.setUpClass.__func__(cls)

    def test_dump_restore_preserves_originals_history_and_mutation_guards(self):
        prior.ReviewPostgresTests.setUp(self)
        prior.ReviewPostgresTests.append(self)
        with self.owner.connect() as c:
            raw=c.connection.driver_connection;raw.autocommit=True
            raw.execute((ROOT/'new-platform/backend/migrations/20261113_level16_staging_evidence.sql').read_text())
            raw.autocommit=False
        original=b'SYNTHETIC_BACKUP_ORIGINAL_NOT_CLINICAL_EVIDENCE'
        with self.owner.begin() as c:
            c.execute(text('INSERT INTO level16_review.original_documents VALUES (:id,:sha,:bytes)'),
                      {'id':'synthetic-backup-document','sha':hashlib.sha256(original).hexdigest(),'bytes':original})
            c.execute(text("INSERT INTO level16_review.authorization_audit(decision,reason) VALUES ('DENIED','TOKEN_REJECTED')"))
        spec=importlib.util.spec_from_file_location('inventory',ROOT/'scripts/medical/level16_backup_inventory.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with self.owner.connect() as c: before=module.inventory(c)
        container=os.environ['LEVEL16_TEST_POSTGRES_CONTAINER_ID']
        if not re.fullmatch(r'[a-f0-9]{12,64}',container) or not re.fullmatch(r'level16_test_[a-f0-9]{32}',self.dbname):
            self.fail('Only the dedicated disposable test container/database may be exported')
        target_name='level16_test_'+uuid4().hex
        with self.bootstrap.connect() as c:c.exec_driver_sql('CREATE DATABASE '+target_name)
        target_owner=create_engine(self.owner.url.set(database=target_name))
        target_runtime=create_engine(self.runtime.url.set(database=target_name))
        try:
            dump=subprocess.run(['docker','exec',container,'pg_dump','-U','postgres','-Fc','--no-owner','-d',self.dbname],
                                check=True,capture_output=True,timeout=60).stdout
            self.assertTrue(dump.startswith(b'PGDMP'))
            # The only backup file is private and temporary; no clinical data or
            # credentials are placed in Git, process arguments or output logs.
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'synthetic-review-backup.dump'
                with path.open('xb') as f:f.write(dump)
                path.chmod(0o600)
                subprocess.run(['docker','exec','-i',container,'pg_restore','-U','postgres','--no-owner','-d',target_name],
                               input=path.read_bytes(),check=True,capture_output=True,timeout=60)
            with target_owner.connect() as c: after=module.inventory(c)
            self.assertEqual(before,after)
            self.assertEqual(after['tables']['events']['rowCount'],1)
            self.assertEqual(after['tables']['original_documents']['rowCount'],1)
            with target_runtime.begin() as c:
                ReviewEventService(target_runtime)._storage(c)
                self.assertEqual(c.execute(text('SELECT count(*) FROM level16_review.original_documents')).scalar(),0)
            for engine,statement in ((target_runtime,'DELETE FROM level16_review.events'),
                                     (target_owner,'DELETE FROM level16_review.events'),
                                     (target_owner,'TRUNCATE level16_review.original_documents')):
                with self.assertRaises(DBAPIError):
                    with engine.begin() as c:c.exec_driver_sql(statement)
        finally:
            target_runtime.dispose();target_owner.dispose()
            with self.bootstrap.connect() as c:c.exec_driver_sql('DROP DATABASE '+target_name+' WITH (FORCE)')


if __name__=='__main__':unittest.main()
