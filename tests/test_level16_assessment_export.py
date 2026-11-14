"""The website runner receives reproducible, source-bound owner research only."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('export',ROOT/'scripts/medical/export_level16_assessment_evidence.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class AssessmentExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=m.build()

    def test_committed_package_reproduces_retained_research_inputs(self):
        self.assertEqual(json.loads(m.OUTPUT.read_text(encoding='utf-8')),self.data)
        self.assertEqual(len(self.data['sourceSnapshotDigests']),4)

    def test_32_trials_192_levels_and_unmapped_exceptions_are_preserved(self):
        self.assertEqual(len(self.data['trials']),32)
        self.assertEqual(sum(len(t['levels']) for t in self.data['trials']),192)
        self.assertEqual({t['nct'] for t in self.data['trials'] if not t['provisionalApplicationCycleIds']},
            {'NCT05031780','NCT06553768','NCT06747468'})
        self.assertFalse(self.data['externalVerificationRequired'])
        self.assertFalse(self.data['historicalPredictionInputPermitted'])
        self.assertEqual(self.data['ownerReviewStatus'],'OWNER_NOT_REVIEWED')

    def test_no_original_bytes_or_legacy_authorization_requirements_are_packaged(self):
        text=json.dumps(self.data)
        for forbidden in ('localPath','originalBytes','scientificReviewRequirements','independent_source_authentication','privateKey'):
            self.assertNotIn(forbidden,text)
        trial=next(t for t in self.data['trials'] if t['nct']=='NCT04576949')
        self.assertEqual(len(trial['sources']),12)  # 11 dossier sources plus the linked PubMed abstract record
        self.assertIsNone(trial['statisticalChronology']['actualUnblindingDate'])

    def test_orca3_columns_keep_published_counts_and_table_intervals(self):
        trial=next(t for t in self.data['trials'] if t['nct']=='NCT05206370')
        comparison=trial['reportedComparisons'][0]
        self.assertEqual((comparison['activeAbstinent'],comparison['activeRandomized'],comparison['activePct']),(39,263,14.8))
        self.assertEqual(comparison['ci95Reported'],[1.5,5.6])
        self.assertTrue(all(f['sourceUrl'] in {s['url'] for s in trial['sources']} for l in trial['levels'] for f in l['facts']))

if __name__=='__main__':unittest.main()
