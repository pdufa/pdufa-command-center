"""Synthetic-only tests: intake completeness never means scientific completion."""
import copy
import importlib.util
import unittest
from pathlib import Path

from test_phase_first_levels_1_6 import fixture

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/medical' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cases = load('level16_review_cases')
engine = load('phase_first_levels_1_6')
preview = load('render_level16_focus_preview')


class ReviewCasesTests(unittest.TestCase):
    def setUp(self):
        self.roster, self.apps, self.definition = fixture()
        self.nct = self.roster['records'][0]['nct']
        self.source = {'submissionId': 'source-1', 'level': 3,
                       'sourceUrl': 'https://example.org/original', 'sourceDate': '2026-11-01',
                       'accessedDate': '2026-11-02', 'submittedDigestUnverified': 'a' * 64,
                       'candidateApplicationCycleId': None}
        self.sources = {self.nct: [self.source]}
        self.case = {key: self.source[key] for key in (
            'submissionId', 'sourceUrl', 'sourceDate', 'accessedDate', 'candidateApplicationCycleId')}
        self.case.update(nct=self.nct, documentSha256='a' * 64,
                         checks={key: {'state': 'UNREVIEWED', 'observation': 'Requires original-source review',
                                       'locator': 'Page 1'} for key in cases.CHECKS},
                         conflicts=[], limitations=['Original publication ownership not authenticated'])
        self.proposal = dict(proposalId='proposal-1', nct=self.nct, level=3,
                             candidateApplicationCycleId=None, sourceSubmissionIds=['source-1'],
                             phaseBasis=['PHASE2'], evidenceState='UNREVIEWED',
                             findings=['Synthetic proposed finding <script>alert(1)</script>'],
                             reasons=['Synthetic reason'], contradictoryEvidence=[],
                             limitations=['No authenticated clinical evidence'],
                             reviewerIdentityClaim='claimed reviewer', reviewDate='2026-11-14',
                             challenge=dict.fromkeys(('reviewerIdentityClaim', 'reviewDate', 'findings', 'limitations')),
                             outstandingBlockers=[])

    def doc(self, rows, kind):
        return dict(schemaVersion=1, kind='FOCUS_LEVELS_1_6_' + kind,
                    cutoffDate='2026-11-13', records=rows)

    def run_cases(self):
        return cases.prepare(self.sources, '2026-11-13', self.doc([self.case], 'SOURCE_CASES'),
                             self.doc([self.proposal], 'REVIEW_PROPOSALS'))

    def test_all_six_levels_stay_unreviewed_even_with_matching_bytes_and_named_challenge(self):
        self.source['localByteReceipt'] = {'byteMatchStatus': 'LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY'}
        self.proposal['challenge'] = dict(reviewerIdentityClaim='second claimed person', reviewDate='2026-11-15',
                                          findings=['Agrees'], limitations=['Identity not authenticated'])
        for level in range(1, 7):
            self.source['level'] = self.proposal['level'] = level
            dossiers, proposals = self.run_cases()
            self.assertFalse(dossiers['source-1']['independentlyAuthenticated'])
            self.assertIn('AUTHENTICATED_SOURCE_REVIEW_REQUIRED', dossiers['source-1']['blockers'])
            proposed = proposals[self.nct][level][0]
            self.assertFalse(proposed['independentlyReviewed'])
            self.assertFalse(proposed['prospectiveBlindAssessment'])
            self.assertEqual(proposed['challenge']['status'], 'IDENTITY_AND_CHALLENGE_UNVERIFIED')

    def test_missing_and_nonpublic_checks_preserved_as_blockers(self):
        for state in ('MISSING', 'NOT_PUBLICLY_AVAILABLE'):
            self.case['checks']['protocolVersion']['state'] = state
            d, _ = self.run_cases()
            self.assertIn('protocolVersion:' + state, d['source-1']['blockers'])

    def test_conflicts_require_details_and_remain_blocked(self):
        self.case['checks']['phase']['state'] = 'CONFLICTING'
        with self.assertRaises(ValueError): self.run_cases()
        self.case['conflicts'] = ['Registry and protocol disagree on phase']
        d, _ = self.run_cases()
        self.assertIn('SOURCE_CONFLICT_RECONCILIATION_REQUIRED', d['source-1']['blockers'])
        self.proposal['evidenceState'] = 'CONFLICTING'
        with self.assertRaises(ValueError): self.run_cases()
        self.proposal['contradictoryEvidence'] = ['Alternative source contradicts proposed finding']
        self.run_cases()

    def test_exact_nct_application_and_document_binding(self):
        for key, value in (('nct', 'NCT99999999'), ('candidateApplicationCycleId', 'invented'),
                           ('documentSha256', 'b' * 64), ('sourceUrl', 'https://example.org/modified'),
                           ('sourceDate', '2026-11-02'), ('accessedDate', '2026-11-03')):
            original = self.case[key]
            self.case[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.run_cases()
            self.case[key] = original

    def test_cross_trial_level_application_and_unknown_evidence_rejected(self):
        for key, value in (('nct', 'NCT99999999'), ('level', 4), ('level', True),
                           ('candidateApplicationCycleId', 'invented'), ('sourceSubmissionIds', ['unknown']),
                           ('sourceSubmissionIds', ['source-1', 'source-1'])):
            original = self.proposal[key]
            self.proposal[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.run_cases()
            self.proposal[key] = original

    def test_no_certification_probability_or_outcome_fields(self):
        for row in (self.case, self.proposal):
            for key in ('verified', 'reviewerAuthenticated', 'approvalProbability', 'score', 'historicalOutcome'):
                row[key] = True
                with self.assertRaises(ValueError): self.run_cases()
                del row[key]
        self.case['checks']['phase']['state'] = 'VERIFIED'
        with self.assertRaises(ValueError): self.run_cases()

    def test_phase_first_waiver_only_early_results_and_statistics(self):
        self.proposal['evidenceState'] = 'NOT_YET_EXPECTED_AT_THIS_PHASE'
        for phase in ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA'):
            for level in range(1, 7):
                self.source['level'] = self.proposal['level'] = level
                self.proposal['phaseBasis'] = [phase]
                if phase in ('EARLY_PHASE1', 'PHASE1', 'PHASE2') and level in (3, 5):
                    self.run_cases()
                else:
                    with self.assertRaises(ValueError): self.run_cases()

    def test_identity_checks_cannot_be_phase_waived(self):
        self.case['checks']['exactNct']['state'] = 'NOT_YET_EXPECTED_AT_THIS_PHASE'
        with self.assertRaises(ValueError): self.run_cases()

    def test_missing_phase_and_identity_rejected(self):
        for key, value in (('phaseBasis', []), ('reviewerIdentityClaim', ''), ('reviewDate', '2026-11-01')):
            original = self.proposal[key]
            self.proposal[key] = value
            with self.assertRaises(ValueError): self.run_cases()
            self.proposal[key] = original

    def test_self_challenge_and_backdated_challenge_rejected(self):
        self.proposal['challenge'] = dict(reviewerIdentityClaim='claimed reviewer', reviewDate='2026-11-15',
                                          findings=['Agrees'], limitations=[])
        with self.assertRaises(ValueError): self.run_cases()
        self.proposal['challenge'].update(reviewerIdentityClaim='another claim', reviewDate='2026-11-13')
        with self.assertRaises(ValueError): self.run_cases()

    def test_duplicate_cases_and_proposals_rejected(self):
        for source_doc, review_doc in ((self.doc([self.case, self.case], 'SOURCE_CASES'), None),
                                       (None, self.doc([self.proposal, self.proposal], 'REVIEW_PROPOSALS'))):
            with self.assertRaises(ValueError):
                cases.prepare(self.sources, '2026-11-13', source_doc, review_doc)

    def test_duplicate_document_and_modified_document_are_not_corroboration(self):
        other = dict(self.source, submissionId='source-2')
        self.sources[self.nct].append(other)
        dossiers, _ = self.run_cases()
        self.assertEqual(dossiers['source-1']['sameDigestSubmissionIds'], ['source-2'])
        self.assertIn('DUPLICATE_DOCUMENT_NOT_INDEPENDENT_CORROBORATION', dossiers['source-1']['blockers'])
        other['submittedDigestUnverified'] = 'b' * 64
        dossiers, _ = self.run_cases()
        self.assertEqual(dossiers['source-1']['sameUrlDifferentDigestSubmissionIds'], ['source-2'])
        self.assertIn('SOURCE_DOCUMENT_VARIANTS_REQUIRE_RECONCILIATION', dossiers['source-1']['blockers'])

    def test_empty_findings_reasons_or_limitations_rejected(self):
        for key in ('findings', 'reasons', 'limitations'):
            original = self.proposal[key]
            self.proposal[key] = []
            with self.assertRaises(ValueError): self.run_cases()
            self.proposal[key] = original

    def test_cutoff_mismatch_rejected(self):
        doc = self.doc([self.case], 'SOURCE_CASES')
        doc['cutoffDate'] = '2026-11-14'
        with self.assertRaises(ValueError): cases.prepare(self.sources, '2026-11-13', doc)

    def test_integrated_report_preview_no_promotion_or_mutation(self):
        submission = dict(self.source)
        submission.pop('submittedDigestUnverified')
        submission.update(nct=self.nct, documentSha256='a' * 64, sourceKind='JOURNAL_PUBLICATION',
                          locator='Page 1', claim='Synthetic source lead', role='SUPPORTS', submittedBy='intake')
        document = self.doc([submission], 'SOURCE_SUBMISSIONS')
        before = copy.deepcopy((self.roster, self.apps, self.definition, document))
        report = engine.build(self.roster, self.apps, {'results': {}}, self.definition,
                              submissions=document, source_cases=self.doc([self.case], 'SOURCE_CASES'),
                              review_proposals=self.doc([self.proposal], 'REVIEW_PROPOSALS'))
        self.assertEqual(before, (self.roster, self.apps, self.definition, document))
        self.assertEqual(report['focusTrialCount'], 32)
        self.assertEqual(report['sourceVerificationCaseCount'], 1)
        self.assertEqual(report['unreviewedProposalCount'], 1)
        self.assertEqual(report['originalSourcesIndependentlyAuthenticated'], 0)
        self.assertEqual(report['scientificallyAdjudicatedLevels'], 0)
        self.assertEqual(report['unmappedTrialCount'], 3)
        for trial in report['trials']:
            for level in trial['levels']:
                self.assertIsNone(level['scientificConclusion'])
                self.assertIsNone(level['approvalProbability'])
                self.assertFalse(level['assessmentCompleted'])
        html = preview.render(report)
        self.assertIn('Abivax S.A.', html)
        self.assertIn('NOT_MAPPED_APPLICATION_CYCLE', html)
        self.assertIn('Registry phase/status (captured, NOT verified)', html)
        self.assertIn('UNREVIEWED review proposal', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('Source verification case: UNREVIEWED', html)
        proposal = report['trials'][0]['levels'][2]['reviewProposalsUnreviewed'][0]
        proposal['independentlyReviewed'] = True
        with self.assertRaises(ValueError): preview.render(report)


if __name__ == '__main__': unittest.main()
