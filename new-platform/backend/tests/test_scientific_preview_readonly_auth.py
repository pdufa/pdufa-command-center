"""Credential separation for isolated scientific read-only preview GET.

This fixture never reads production credentials, calls network, or writes data.
"""
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response
from app import main

OLD = "fixture-ordinary-private-auth-key"
READ = "scientific-preview-only-read-" + ("z" * 48)
ISOLATED = "srv-dbehn9fb9u1s739ok5vg"


def context(service_id=ISOLATED, freeze="true", preview_key=READ):
    return patch.dict(os.environ, {
        "PDUFA_INTERNAL_API_KEY": OLD,
        "PDUFA_SCIENTIFIC_PREVIEW_READ_KEY": preview_key,
        "RENDER_SERVICE_ID": service_id,
        "PDUFA_MIGRATION_READ_ONLY": freeze,
    }, clear=True)


class IsolatedScientificReadOnlyCredentialTests(unittest.TestCase):
    def test_preview_key_accepted_only_on_frozen_isolated_service(self):
        with context():
            self.assertIsNone(main.require_isolated_scientific_read_key(READ))
            self.assertIsNone(main.require_isolated_scientific_read_key(OLD))
            with self.assertRaises(HTTPException) as caught:
                main.require_internal_key(READ)
            self.assertEqual(caught.exception.status_code, 401)

    def test_different_render_service_and_unfrozen_mode_reject_preview(self):
        for service, freeze in (
            ("srv-production-placeholder", "true"),
            (ISOLATED, "false"),
            (ISOLATED, ""),
            ("", "true"),
        ):
            with self.subTest(service=service, freeze=freeze), context(service, freeze):
                with self.assertRaises(HTTPException) as caught:
                    main.require_isolated_scientific_read_key(READ)
                self.assertEqual(caught.exception.status_code, 401)
                self.assertIsNone(main.require_internal_key(OLD))

    def test_no_preview_key_or_short_key_is_never_an_auth_bypass(self):
        for supplied in ("", "not-long-enough"):
            with self.subTest(key=supplied), context(preview_key=supplied):
                with self.assertRaises(HTTPException) as caught:
                    main.require_isolated_scientific_read_key(supplied)
                self.assertEqual(caught.exception.status_code, 401)
        with context():
            for supplied in (None, "", READ + "not-a-match"):
                with self.subTest(supplied=supplied), self.assertRaises(HTTPException) as caught:
                    main.require_isolated_scientific_read_key(supplied)
                self.assertEqual(caught.exception.status_code, 401)

    def test_preview_key_cannot_unlock_any_other_scientific_endpoint(self):
        permitted = {
            "/api/scientific-assessment",
            "/api/scientific-assessment/pilot/keynote024",
            "/api/scientific-assessment/dossier",
            "/api/scientific-assessment/captured-source-manifest/{nct_id}",
        }
        permitted_seen = set()
        for route in main.app.routes:
            if not getattr(route, "path", "").startswith("/api/scientific-assessment"):
                continue
            dependencies = getattr(route, "dependant", None)
            if dependencies is None:
                continue
            uses_preview = any(dep.call is main.require_isolated_scientific_read_key
                               for dep in dependencies.dependencies)
            if uses_preview:
                self.assertEqual(route.methods, {"GET"},
                                 "Preview key must never reach a write route")
                self.assertIn(route.path, permitted,
                              "Preview read key must not reach any other endpoint")
                permitted_seen.add(route.path)
        self.assertEqual(permitted_seen, permitted)
        # This fourth permission can expose only hash metadata for the one
        # frozen pilot; never document bytes, reviewer data or other NCTs.
        metadata_route = next(r for r in main.app.routes if getattr(r, "path", "") ==
                              "/api/scientific-assessment/captured-source-manifest/{nct_id}")
        self.assertEqual(metadata_route.methods, {"GET"})
        with context():
            with self.assertRaises(HTTPException) as caught:
                main.scientific_pilot_captured_source_manifest("NCT00000001", Response())
            # In a unit invocation the extra service guard fails unless
            # DATABASE_URL is configured for the isolated PostgreSQL service.
            self.assertIn(caught.exception.status_code, (403, 422))
        # The underlying ordinary key remains mandatory for storage,
        # reviewers, bulk archives, and other non-public operations.
        for path in (
            "/api/scientific-assessment/storage-status",
            "/api/scientific-assessment/batches",
            "/api/scientific-assessment/dossier/references",
        ):
            route = next(r for r in main.app.routes if getattr(r, "path", "") == path)
            self.assertTrue(any(dep.call is main.require_internal_key
                                for dep in route.dependant.dependencies), path)

    def test_legacy_key_preserved_and_http_contract_marks_only_transport(self):
        with context():
            self.assertIsNone(main.require_internal_key(OLD))
            self.assertIsNone(main.require_isolated_scientific_read_key(READ))
            response = Response()
            body = main.get_scientific_assessment("TRIAL|NCT12345678", response)
            self.assertEqual(response.headers["x-pdufa-scientific-api-contract"],
                             "science-integrated-v1")
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertIsNone(body["assessment"]["overall_score"])
            self.assertTrue(body["independentOfQualificationPresets"])
            self.assertEqual(body["exactId"], "TRIAL|NCT12345678")


if __name__ == "__main__":
    unittest.main()
