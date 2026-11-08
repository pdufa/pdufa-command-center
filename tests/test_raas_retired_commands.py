"""Permanent retirement protects historical files before any retired command I/O."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class RetiredCommandTests(unittest.TestCase):
    def test_original_workflows_are_byte_preserved_but_not_registered(self):
        manifest=json.loads((ROOT/'archives/raas/workflows/manifest.json').read_text())
        self.assertTrue(manifest['workflows'])
        for item in manifest['workflows']:
            with self.subTest(path=item['originalPath']):
                self.assertFalse((ROOT/item['originalPath']).exists())
                self.assertEqual(hashlib.sha256((ROOT/item['archivePath']).read_bytes()).hexdigest(),item['sha256'])
                self.assertTrue(item['archivePath'].endswith('.disabled'))
    def test_all_retired_commands_stop_before_optional_imports_network_or_output(self):
        manifest=json.loads((ROOT/'archives/raas/cli/manifest.json').read_text())
        self.assertTrue(manifest['commands'])
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'must-not-exist.json'
            env={**os.environ,'RAAS_SCAN_OUTPUT':str(destination),'RAAS_TWO_YEAR_RESULT_PATH':str(destination),'RAAS_RECEIPT_OUTPUT':str(destination)}
            for item in manifest['commands']:
                with self.subTest(path=item['originalPath']):
                    original=ROOT/item['archivePath']
                    self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),item['sha256'])
                    path=ROOT/item['originalPath'];command=[sys.executable if path.suffix=='.py' else 'node',str(path)]
                    result=subprocess.run(command,cwd=tmp,env=env,capture_output=True,text=True,timeout=10)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('RAAS_PERMANENTLY_RETIRED',result.stdout+result.stderr)
                    self.assertNotIn('ModuleNotFoundError',result.stderr)
                    self.assertFalse(destination.exists())
    def test_focus_sync_keeps_sources_and_cannot_write_scores_or_histories(self):
        source=(ROOT/'.github/workflows/p3-post-data-google-sheet-sync.yml').read_text()
        for required in ('auto_promote_p3_post_data.py','refresh_existing_p3_post_data.py','sync_p3_post_data_from_google_sheet.py'):
            self.assertIn(required,source)
        for forbidden in ('bottom-only-recalculate','sync_bottom_clinical_ratings','bottomOnlyScoreHistory','bottomOnlyReviewedGradeIncrement'):
            self.assertNotIn(forbidden,source)
        self.assertNotIn('setup-node',source)
if __name__=='__main__':unittest.main()
