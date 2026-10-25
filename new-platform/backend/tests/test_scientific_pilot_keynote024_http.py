"""Read-only endpoint contracts for the historic KEYNOTE-024 pilot.

All storage is mocked; no live database, external service, or deployment needed.
"""
import gzip
import hashlib
import json
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, require_storage


class Keynote024PilotHttpTests(unittest.TestCase):
    def setUp(self):
        source = {"protocolSection": {
            "identificationModule": {"nctId": "NCT02142738"},
            "designModule": {"designInfo": {
                "allocation": "RANDOMIZED", "maskingInfo": {"masking": "NONE"}},
                "enrollmentInfo": {"count": 305}},
        }}
        raw = json.dumps(source, sort_keys=True,
                         separators=(",", ":"), ensure_ascii=False).encode()
        self.record = SimpleNamespace(
            payload_gzip=gzip.compress(raw), sha256=hashlib.sha256(raw).hexdigest(),
            fetched_at=datetime(2026, 10, 24, tzinfo=timezone.utc),
        )
        app.dependency_overrides[require_storage] = lambda: None
        self.client = TestClient(app)
        self.header = {"x-pdufa-internal-key": "historical-pilot-test-secret"}
        self.env = patch.dict(os.environ, {
            "PDUFA_INTERNAL_API_KEY": "historical-pilot-test-secret",
        })
        self.env.start()
        self.db = patch("app.main.Session")
        self.Session = self.db.start()
        self.Session.return_value.__enter__.return_value.get.return_value = self.record

    def tearDown(self):
        self.db.stop()
        self.env.stop()
        app.dependency_overrides.clear()
        self.client.close()

    def get(self, authenticated=True):
        return self.client.get(
            "/api/scientific-assessment/pilot/keynote024",
            headers=self.header if authenticated else {},
        )

    def test_requires_authentication_without_touching_database(self):
        response = self.get(authenticated=False)
        self.assertEqual(response.status_code, 401)
        self.Session.assert_not_called()

    def test_no_archive_returns_404(self):
        self.Session.return_value.__enter__.return_value.get.return_value = None
        self.assertEqual(self.get().status_code, 404)

    def test_corrupt_archive_fails_closed(self):
        self.record.sha256 = "0" * 64
        response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("publishedResults", response.json())

    def test_research_response_contains_separate_results_and_no_scores(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        result = response.json()
        self.assertEqual(result["dossier"]["nct_id"], "NCT02142738")
        self.assertEqual(result["pilot"]["nct_id"], "NCT02142738")
        self.assertEqual(result["publishedResults"]["nct_id"], "NCT02142738")
        audit = result["sourceEvidenceAudit"]
        self.assertEqual(audit["nctId"], "NCT02142738")
        self.assertEqual(audit["earlyDesignEvidence"]["publicationDate"], "2015-05-20")
        self.assertFalse(audit["earlyDesignEvidence"]["signedSapVerified"])
        self.assertFalse(audit["independentProtocolSapReviewComplete"])
        self.assertEqual(audit["registrySafety"]["status"], "no_groups_documented_in_snapshot")
        self.assertTrue(audit["registrySafety"]["missingGroupsDoNotImplyZeroEvents"])
        safety = result["publishedSafetyReconciliation"]
        self.assertEqual(safety["original2016"]["asTreated"], {
            "pembrolizumab": 154, "chemotherapy": 150,
        })
        self.assertEqual(safety["original2016"]["randomized"], {
            "pembrolizumab": 154, "chemotherapy": 151,
        })
        self.assertEqual(safety["updated2019"]["publicationDate"], "2019-01-08")
        self.assertEqual(safety["updated2019"]["reportedGrade3to5TreatmentRelatedPercent"]["pembrolizumab"], 31.2)
        self.assertFalse(safety["registryReconciliation"]["crossSystemAEReconciliationCompleted"])
        self.assertFalse(safety["inputReadinessGradeChanged"])
        self.assertFalse(safety["reluctanceGradeChanged"])
        self.assertIsNone(safety["scientificScore"])
        self.assertIsNone(safety["fdaApprovalProbability"])
        self.assertIsNone(audit["scientificScore"])
        self.assertIsNone(audit["fdaApprovalProbability"])
        self.assertEqual(len(result["publishedResults"]["analysis_snapshots"]), 3)
        self.assertIsNone(result["dossier"]["overall_score"])
        self.assertIsNone(result["publishedResults"]["overall_score"])
        self.assertIsNone(result["publishedResults"]["fda_approval_probability"])
        interim = result["publishedInterimDesign"]
        european = result["europeanRegistryCrosscheck"]
        self.assertEqual(european["registry"]["eudractNumber"], "2014-000323-25")
        self.assertEqual(european["registry"]["firstRecordEnteredDate"], "2014-06-19")
        self.assertEqual(european["registry"]["sponsorProtocolCode"], "MK-3475-024")
        self.assertFalse(european["registry"]["individualEndpointFieldVersionDated"])
        self.assertFalse(european["registry"]["original2014FieldContentAuthenticated"])
        self.assertFalse(european["registry"]["signed2016SAPAvailable"])
        self.assertEqual(european["eventTiming"]["euPfsEventsTargetApprox"], 175)
        self.assertEqual(european["eventTiming"]["reportedPfsEventsObserved"], 189)
        self.assertEqual(european["eventTiming"]["euOsFirstDeathsTargetApprox"], 110)
        self.assertEqual(european["eventTiming"]["reportedOsInterimDeathsObserved"], 108)
        self.assertFalse(european["researchConclusions"]["preInterimSignedSapVerified"])
        self.assertFalse(european["researchConclusions"]["inputReadinessGradeChanged"])
        self.assertFalse(european["researchConclusions"]["reluctanceGradeChanged"])
        self.assertIsNone(european["scientificScore"])
        self.assertIsNone(european["fdaApprovalProbability"])
        self.assertEqual(interim["reportedDesign"]["overallOneSidedAlphaPercent"], 2.5)
        self.assertEqual(interim["reportedDesign"]["firstInterim"]["reportedAllocatedOneSidedAlphaPercent"], 0.5)
        self.assertEqual(interim["reportedDesign"]["secondInterim"]["reportedAllocatedOneSidedAlphaPercent"], 2.0)
        self.assertEqual(interim["observedInterim"]["reportedPfsEvents"], 189)
        self.assertEqual(interim["observedInterim"]["reportedDeaths"], 108)
        self.assertEqual(interim["observedInterim"]["fdaStaffReportedOsAllocatedAlpha"], 0.0118)
        self.assertFalse(interim["sourceDateContext"]["contemporaneousSapAuthenticated"])
        self.assertFalse(interim["reconciliation"]["inputReadinessGradeChanged"])
        self.assertFalse(interim["reconciliation"]["reluctanceGradeChanged"])
        self.assertIsNone(interim["scientificScore"])
        self.assertIsNone(interim["fdaApprovalProbability"])
        self.assertEqual(result["scientificReadiness"]["inputReadiness"]["grade"], "FAIL")
        self.assertEqual(result["scientificReadiness"]["reluctance"]["grade"], "HIGH")
        self.assertTrue(result["scientificReadiness"]["protocol"]["afterInterimDataCutoff"])
        self.assertIsNone(result["scientificReadiness"]["scientificScore"])
        self.assertIsNone(result["scientificReadiness"]["fdaApprovalProbability"])
        self.assertFalse(result["scoringModified"])
        self.assertFalse(result["qualificationPresetsModified"])
        self.assertTrue(result["researchOnly"])
        self.Session.return_value.__enter__.return_value.get.assert_called_once()

    def test_corrupt_registry_safety_event_group_rejected_before_response(self):
        import json
        source = {
            "protocolSection": {"identificationModule": {"nctId": "NCT02142738"}},
            "resultsSection": {
                "adverseEventsModule": {"eventGroups": [{
                    "id": "EG000", "title": "bad fixture",
                    "seriousNumAffected": 11, "seriousNumAtRisk": 10,
                }]},
            },
        }
        raw = json.dumps(source, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode()
        self.record.payload_gzip = gzip.compress(raw)
        self.record.sha256 = hashlib.sha256(raw).hexdigest()
        response = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sourceEvidenceAudit", response.json())

    def test_no_live_lookup_or_background_scan_in_endpoint(self):
        with patch("app.scientific_external_sources._read_json") as external:
            response = self.get()
            self.assertEqual(response.status_code, 200)
            external.assert_not_called()


if __name__ == "__main__":
    unittest.main()
