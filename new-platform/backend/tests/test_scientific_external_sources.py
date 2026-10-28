"""Offline contract tests for PubMed/FDA source lookups and safe dossier attachment."""
import copy
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.scientific_dossier import build_scientific_dossier
from app.scientific_external_sources import (
    SourceLookupError, _read_json, attach_research_references,
    lookup_fda_application, lookup_pubmed_nct, MAX_RESPONSE_BYTES,
)


class ScientificExternalSourcesTests(unittest.TestCase):
    def setUp(self):
        self.nct = "NCT12345678"
        self.registry = {"protocolSection": {
            "identificationModule": {"nctId": self.nct},
            "designModule": {"designInfo": {"allocation": "RANDOMIZED"}},
        }}
        self.dossier = build_scientific_dossier("TRIAL|" + self.nct, self.nct, self.registry)

    @patch("app.scientific_external_sources._read_json")
    def test_pubmed_search_is_exact_and_safely_unscored(self, get_json):
        get_json.side_effect = [
            {"esearchresult": {"idlist": ["12345", "56789"]}},
            {"result": {"uids": ["12345", "56789"],
                "12345": {"uid": "12345", "title": "A trial report",
                          "fulljournalname": "Journal One", "pubdate": "2025"},
                "56789": {"uid": "56789", "title": "An editorial",
                          "fulljournalname": "Journal Two", "pubdate": "2024"},
            }},
        ]
        result = lookup_pubmed_nct(self.nct)
        self.assertEqual(result["status"], "indexed_references_found")
        self.assertEqual(len(result["references"]), 2)
        self.assertTrue(all(x["trial_result_confirmed"] is False for x in result["references"]))
        self.assertIn("NCT12345678", get_json.call_args_list[0].args[0])
        self.assertTrue(get_json.call_args_list[0].args[0].startswith(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        ))

    @patch("app.scientific_external_sources._read_json")
    def test_pubmed_zero_references_means_no_claim(self, get_json):
        get_json.return_value = {"esearchresult": {"idlist": []}}
        result = lookup_pubmed_nct(self.nct)
        self.assertEqual(result["status"], "no_indexed_references_found")
        self.assertEqual(result["references"], [])
        get_json.assert_called_once()

    @patch("app.scientific_external_sources._read_json")
    def test_pubmed_rejects_search_and_summary_identity_mismatch(self, get_json):
        get_json.side_effect = [
            {"esearchresult": {"idlist": ["12345"]}},
            {"result": {"uids": ["22222"], "22222": {"uid": "22222", "title": "Unrelated"}}},
        ]
        with self.assertRaisesRegex(SourceLookupError, "identity mismatch"):
            lookup_pubmed_nct(self.nct)

    @patch("app.scientific_external_sources._read_json")
    def test_pubmed_rejects_missing_summary_identifiers(self, get_json):
        get_json.side_effect = [
            {"esearchresult": {"idlist": ["12345"]}},
            {"result": {"uids": ["12345"], "12345": {"uid": "99887", "title": "Wrong"}}},
        ]
        with self.assertRaisesRegex(SourceLookupError, "identity mismatch"):
            lookup_pubmed_nct(self.nct)

    @patch("app.scientific_external_sources._read_json")
    def test_fda_exact_application_is_unlinked_metadata(self, get_json):
        get_json.return_value = {"results": [{
            "application_number": "NDA012345", "sponsor_name": "Company",
            "products": [{"brand_name": "ExampleDrug"}],
            "submissions": [{"submission_status": "AP"}],
        }]}
        result = lookup_fda_application("NDA012345")
        self.assertEqual(result["status"], "application_found")
        record = result["references"][0]
        self.assertFalse(record["trial_association_verified"])
        self.assertFalse(record["scientifically_verified"])
        self.assertNotIn("submissions", record)
        self.assertIn("application_number", get_json.call_args.args[0])
        self.assertIn("NDA012345", get_json.call_args.args[0])

    @patch("app.scientific_external_sources._read_json")
    def test_fda_unknown_application_is_not_negative_evidence(self, get_json):
        get_json.return_value = {"results": []}
        result = lookup_fda_application("BLA012345")
        self.assertEqual(result["status"], "application_not_found")
        self.assertEqual(result["references"], [])

    @patch("app.scientific_external_sources._read_json")
    def test_fda_wrong_application_rejected(self, get_json):
        get_json.return_value = {"results": [{"application_number": "NDA000001"}]}
        with self.assertRaisesRegex(SourceLookupError, "mismatch"):
            lookup_fda_application("NDA012345")

    def test_invalid_identifier_never_triggers_requests(self):
        with patch("app.scientific_external_sources._read_json") as fetch:
            for nct in ("BAD", "NCT1234567", "NCT12345678&foo=bar"):
                with self.assertRaises(ValueError):
                    lookup_pubmed_nct(nct)
            for app in ("NDA123456&x", "12345", "ANDA012345"):
                with self.assertRaises(ValueError):
                    lookup_fda_application(app)
            fetch.assert_not_called()

    def test_references_attach_without_mutating_dossier_or_scores(self):
        before = copy.deepcopy(self.dossier)
        pubmed = {"requested_nct_id": self.nct, "references": [{
            "kind": "pubmed_citation", "pmid": "12345", "scientifically_verified": False
        }]}
        fda = {"requested_application_number": "NDA012345", "references": [{
            "kind": "drugs_at_fda_application", "application_number": "NDA012345",
            "scientifically_verified": False,
        }]}
        merged = attach_research_references(self.dossier, pubmed, fda)
        self.assertEqual(self.dossier, before)
        self.assertEqual(len(merged["domains"]["clinical_results"]["research_leads"]), 1)
        self.assertEqual(len(merged["domains"]["regulatory_analysis"]["research_leads"]), 1)
        self.assertTrue(all(d["score"] is None for d in merged["domains"].values()))
        self.assertIsNone(merged["overall_score"])
        self.assertIsNone(merged["fda_approval_probability"])
        self.assertEqual(merged["external_research_status"], "references_only")

    def test_foreign_nct_references_rejected(self):
        with self.assertRaisesRegex(ValueError, "NCT identity mismatch"):
            attach_research_references(
                self.dossier, {"requested_nct_id": "NCT87654321", "references": []}
            )

    def test_reject_scored_or_forecast_dossier(self):
        changed = copy.deepcopy(self.dossier)
        changed["domains"]["biology"] = {"score": 90}
        with self.assertRaisesRegex(ValueError, "scores"):
            attach_research_references(changed)
        changed = copy.deepcopy(self.dossier)
        changed["fda_approval_probability"] = 0.9
        with self.assertRaisesRegex(ValueError, "approval probability"):
            attach_research_references(changed)

    @patch("app.scientific_external_sources.urlopen")
    def test_http_payload_size_guard(self, urlopen):
        obj = type("Response", (), {"__enter__": lambda s: s, "__exit__": lambda s, *a: None,
                                    "read": lambda s, n: b"x" * (MAX_RESPONSE_BYTES + 1)})()
        urlopen.return_value = obj
        with self.assertRaisesRegex(SourceLookupError, "size limit"):
            _read_json("https://api.fda.gov/drug/drugsfda.json?limit=1")

    def test_disallow_arbitrary_host(self):
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            _read_json("https://example.com/anything")


if __name__ == "__main__":
    unittest.main()
