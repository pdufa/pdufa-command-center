"""Regression fixtures prove retirement is an execution boundary, not a word ban."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('retirement_guard', ROOT / 'scripts/audit_raas_retirement.py')
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class RetirementGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.write('AGENTS.md', 'RAAS is permanently retired. Preserve historical records read-only.\n')
        self.write('.github/copilot-instructions.md', 'Read AGENTS.md. RAAS is permanently retired. Preserve history read-only.\n')
        self.write('archives/raas/read-only-record-manifest.json', json.dumps({'schemaVersion': 1, 'files': []}))

    def tearDown(self):
        self.directory.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def audit(self):
        return guard.audit(self.root)

    def kinds(self):
        return {v['kind'] for v in self.audit()['violations']}

    def test_independent_analysis_and_historical_records_are_allowed(self):
        self.write('new-platform/frontend/app/focus/page.tsx', 'export default function Page(){return "FOCUS";}')
        history = self.write('new-platform/frontend/data/raas-trial-score-history.json', '{"records":[{"score":65}]}')
        before = history.read_bytes()
        result = self.audit()
        self.assertTrue(result['passed'])
        self.assertEqual(result['historicalReadOnlyRecordFileCount'], 1)
        self.assertEqual(history.read_bytes(), before)

    def test_transitive_import_and_reexport_cannot_hide_retired_engine(self):
        self.write('new-platform/frontend/app/focus/page.tsx', 'import {run} from "../../lib/clinical"; export default run;')
        self.write('new-platform/frontend/lib/clinical.ts', 'export {run} from "./wrapper";')
        self.write('new-platform/frontend/lib/wrapper.ts', 'import {run} from "./raas-engine"; export {run};')
        self.write('new-platform/frontend/lib/raas-engine.ts', 'export const run=()=>75;')
        report = self.audit()
        matches = [v for v in report['violations'] if v['kind'] == 'RETIRED_IMPORT_REACHABLE']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['entrypointChain'][-1], 'new-platform/frontend/lib/raas-engine.ts')

    def test_alias_import_is_resolved(self):
        self.write('new-platform/frontend/app/page.tsx', 'import {analyze} from "@/lib/clinical"; export default analyze;')
        self.write('new-platform/frontend/lib/clinical.ts', 'export {score} from "./raas-scoring";')
        self.write('new-platform/frontend/lib/raas-scoring.ts', 'export const score=50;')
        self.assertIn('RETIRED_IMPORT_REACHABLE', self.kinds())

    def test_dynamic_raas_imports_are_blocked(self):
        self.write('new-platform/frontend/app/api/analyze/route.ts', 'export async function GET(){return import("../../" + "raas-" + "engine");}')
        self.assertIn('RETIRED_DYNAMIC_IMPORT', self.kinds())

    def test_backend_dynamic_and_transitive_imports_are_blocked(self):
        self.write('new-platform/backend/app/main.py', 'from .analysis import analyze\n')
        self.write('new-platform/backend/app/analysis.py', 'import importlib\ndef analyze():\n return importlib.import_module("app.raas_engine")\n')
        self.assertIn('RETIRED_DYNAMIC_IMPORT', self.kinds())

    def test_old_api_fetch_and_score_output_are_blocked(self):
        self.write('new-platform/frontend/app/page.tsx', 'const result={raasScore:75}; fetch("/api/raas-score"); export default result;')
        self.assertIn('RETIRED_API_REQUEST', self.kinds())
        self.assertIn('RETIRED_ACTIVE_ANALYSIS_OUTPUT', self.kinds())

    def test_active_controls_and_automated_sheet_prompts_cannot_reactivate_raas(self):
        self.write('new-platform/frontend/app/page.tsx', 'export default function Page(){return "Open RAAS (search NCT)";}')
        self.write('scripts/refresh_focus.py', 'row={18:"Run RAAS"}\n')
        self.write('.github/workflows/source-sync.yml', 'on: [push]\njobs:\n  refresh:\n    steps:\n      - run: python scripts/refresh_focus.py\n')
        violations = [v for v in self.audit()['violations'] if v['kind'] == 'RETIRED_ACTIVE_CONTROL']
        self.assertEqual({v['path'] for v in violations}, {
            'new-platform/frontend/app/page.tsx', 'scripts/refresh_focus.py'})

    def test_import_free_retirement_tombstone_is_allowed(self):
        self.write('new-platform/frontend/app/raas-review/page.tsx', 'export default function Page(){return "RAAS permanently retired; historical records are read-only.";}')
        self.write('new-platform/frontend/app/api/raas-review/route.ts', 'export function GET(){return Response.json({error:"RAAS retired"},{status:410});}')
        self.assertTrue(self.audit()['passed'])

    def test_explicit_history_archive_may_read_json_but_not_compute_scores(self):
        self.write('new-platform/frontend/data/raas-history.json', '{"records":[]}')
        entry = self.write('new-platform/frontend/app/archive/raas/page.tsx', 'import history from "../../../data/raas-history.json"; export default function Page(){return history.records.length;}')
        self.assertTrue(self.audit()['passed'])
        entry.write_text(entry.read_text() + '\nimport {score} from "../../../lib/raas-score";')
        self.write('new-platform/frontend/lib/raas-score.ts', 'export const score=()=>100;')
        self.assertIn('RETIRED_IMPORT_REACHABLE', self.kinds())

    def test_archive_mutation_route_is_blocked(self):
        self.write('new-platform/frontend/app/api/archive/raas/route.ts', 'export function POST(){return {saved:true};}')
        self.assertIn('HISTORICAL_ARCHIVE_NOT_READ_ONLY', self.kinds())

    def test_registered_retired_workflow_is_not_allowed_even_with_manual_only_trigger(self):
        self.write('.github/workflows/raas-analysis.yml', 'name: Old analysis\non:\n  workflow_dispatch:\njobs:\n  job:\n    if: false\n    steps: []\n')
        self.assertIn('RETIRED_WORKFLOW_REGISTERED', self.kinds())

    def test_archived_workflows_and_historical_path_mentions_are_not_active(self):
        self.write('archives/raas/workflows/raas-analysis.yml.disabled', 'on:\n schedule: daily\nrun: node scripts/raas_score.cjs\n')
        self.write('.github/workflows/ci.yml', 'on: [push]\npaths: ["archives/raas/**"]\njobs:\n  audit:\n    steps:\n      - run: python scripts/audit_raas_retirement.py --check\n')
        self.write('scripts/audit_raas_retirement.py', '# guard fixture\n')
        self.assertTrue(self.audit()['passed'])

    def test_generic_workflow_cannot_reactivate_retired_script(self):
        self.write('scripts/raas_score.py', 'print("would score")\n')
        self.write('.github/workflows/nightly.yml', 'on: [push]\njobs:\n  analyze:\n    steps:\n      - run: |\n          python scripts/raas_score.py\n')
        self.assertIn('RETIRED_SCHEDULED_COMMAND', self.kinds())

    def test_build_install_requirements_are_checked(self):
        self.write('new-platform/frontend/package.json', json.dumps({'scripts': {'build': 'node scripts/raas-required.cjs && next build'}}))
        self.assertIn('RETIRED_INSTALL_OR_DEPLOYMENT_REQUIREMENT', self.kinds())

    def test_installation_tracker_cannot_require_raas(self):
        self.write('new-platform/frontend/app/installation-audit/tasks.ts', 'export const tasks=[{title:"Install RAAS scoring"}];')
        self.assertIn('RETIRED_INSTALLATION_TASK', self.kinds())

    def test_policy_removal_is_a_regression(self):
        (self.root / 'AGENTS.md').unlink()
        self.assertIn('PERMANENT_POLICY_MISSING', self.kinds())

    def test_copilot_policy_removal_or_weakening_is_a_regression(self):
        policy = self.root / '.github/copilot-instructions.md'
        policy.unlink()
        self.assertIn('COPILOT_POLICY_MISSING', self.kinds())
        policy.write_text('Use independent analysis.')
        self.assertIn('COPILOT_POLICY_MISSING', self.kinds())

    def test_historical_manifest_removal_cannot_disable_preservation(self):
        (self.root / 'archives/raas/read-only-record-manifest.json').unlink()
        report = self.audit()
        self.assertFalse(report['passed'])
        self.assertIn('HISTORICAL_MANIFEST_MISSING', {v['kind'] for v in report['violations']})

    def test_historical_manifest_schema_is_required(self):
        self.write('archives/raas/read-only-record-manifest.json', '{"schemaVersion": 1}')
        self.assertIn('HISTORICAL_MANIFEST_INVALID', self.kinds())

    def test_pinned_historical_record_changes_and_deletions_fail(self):
        history = self.write('new-platform/frontend/data/raas-history.json', '{"records":[{"score":65}]}')
        self.write('archives/raas/read-only-record-manifest.json', json.dumps({
            'schemaVersion': 1, 'files': [{
                'path': 'new-platform/frontend/data/raas-history.json',
                'sha256': hashlib.sha256(history.read_bytes()).hexdigest()
            }]
        }))
        self.assertTrue(self.audit()['passed'])
        history.write_text('{"records":[{"score":95}]}')
        self.assertIn('HISTORICAL_RECORD_MODIFIED', self.kinds())
        history.unlink()
        self.assertIn('HISTORICAL_RECORD_DELETED', self.kinds())


if __name__ == '__main__':
    unittest.main()
