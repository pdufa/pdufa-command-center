"""Preparation templates never authorize live access or execute infrastructure."""
import copy
import json
from pathlib import Path
import sys
import unittest

import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'new-platform/backend'))
from app.level16_staging_preparation import app,check_package
from fastapi.testclient import TestClient


class StagingPreparationTests(unittest.TestCase):
    def setUp(self):self.package=json.loads((ROOT/'infra/level16-staging/owner-approval.json').read_text())

    def test_fourteen_decisions_are_precise_and_all_unapproved(self):
        status=check_package(self.package)
        self.assertEqual(len(status['decisionReferencesMissing']),14)
        self.assertFalse(status['liveIntegrationEnabled'])
        self.assertEqual(status['actualAuthenticatedSources'],0)
        self.assertEqual(self.package['recommended']['reviewerMinimumDistinctPeople'],5)
        self.assertTrue(all(v is None or v==[] for v in self.package['configuration'].values()))

    def test_even_filled_references_cannot_authorize_or_activate(self):
        for item in self.package['decisions']:item['approvalReference']='CALLER_SUPPLIED_NOT_AUTHORIZATION'
        status=check_package(self.package)
        self.assertEqual(status['decisionReferencesMissing'],[])
        self.assertEqual(status['status'],'BLOCKED')
        self.assertFalse(status['liveIntegrationEnabled'])
        self.package['liveAccessEnabled']=True
        with self.assertRaises(ValueError):check_package(self.package)

    def test_missing_decisions_are_rejected(self):
        self.package['decisions'].pop()
        with self.assertRaises(ValueError):check_package(self.package)

    def test_liveness_is_not_readiness_or_reviewer_access(self):
        with TestClient(app) as client:
            self.assertEqual(client.get('/livez').status_code,200)
            self.assertEqual(client.get('/readyz').status_code,503)
            for path in ('/staging/levels1-6','/api/internal/levels1-6/reviews/events','/staging/evidence/anything/doc'):
                response=client.get(path)
                self.assertEqual(response.status_code,503)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertNotIn('NCT05507203',response.text)

    def test_blueprint_is_private_manual_new_database_no_owner_runtime_url(self):
        template=yaml.safe_load((ROOT/'infra/level16-staging/render.yaml.example').read_text())
        service=template['services'][0];database=template['databases'][0]
        self.assertEqual(template['previews']['generation'],'off')
        self.assertEqual(service['type'],'pserv');self.assertEqual(service['autoDeployTrigger'],'off')
        self.assertIn('level16_staging_preparation',service['startCommand'])
        self.assertNotIn('healthCheckPath',service)
        self.assertEqual(database['ipAllowList'],[])
        self.assertNotEqual(database['name'],'pdufa-new-staging-db')
        self.assertTrue(all('fromDatabase' not in v for v in service['envVars']))
        self.assertFalse(any('preDeployCommand' in s for s in template['services']))
        self.assertTrue(all(s['type'] not in ('cron','worker') for s in template['services']))

    def test_identity_template_preserves_strict_qualification_contract(self):
        p=json.loads((ROOT/'infra/level16-staging/identity-profile.json.example').read_text())
        self.assertEqual(p['algorithm'],'RS256');self.assertEqual(p['accessTokenType'],'at+jwt')
        self.assertTrue(p['strictSingleAudience']);self.assertFalse(p['liveAccessEnabled'])
        self.assertIn('sid',p['requiredClaims']);self.assertIn('nbf',p['requiredClaims'])
        self.assertIsNone(p['issuer']);self.assertIsNone(p['audience']);self.assertEqual(p['approvedPublicKeys'],{})


if __name__=='__main__':unittest.main()
