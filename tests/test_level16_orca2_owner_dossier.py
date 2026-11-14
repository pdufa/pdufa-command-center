"""ORCA-2 source reconciliation tests; no private originals or live credentials."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports/scientific-levels1-6'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

m=load('orca2','scripts/medical/level16_orca2_owner_dossier.py')
preview=load('preview_fixture','tests/test_render_level16_focus_preview.py')


class Orca2OwnerDossierTests(unittest.TestCase):
    def setUp(self):
        self.packet=json.loads((REPORTS/'orca2-owner-research-dossier-20261114-v1.json').read_text(encoding='utf-8'))
        self.ncts=[t['nct'] for t in json.loads((ROOT/'new-platform/frontend/data/p3PostDataActive.json').read_text())['records']]

    def validate(self):return m.validate_packet(self.packet,self.ncts)

    def source(self,id):return next(s for s in self.packet['sourceInventory'] if s['id']==id)

    def receipt(self,raw):
        return {'documentSha256':hashlib.sha256(raw).hexdigest(),'byteCount':len(raw),'retrievedAt':'2026-11-14T00:00:00Z','sourceUrl':'https://example.test/synthetic',
            'evidenceCutoffDate':'2026-11-14','state':'HASH_CHECKED','provenanceIndependentlyAuthenticated':False,'independentlyScientificallyReviewed':False}

    def test_committed_packet_has_six_distinct_dossiers_and_realistic_gates(self):
        self.assertEqual(len(self.validate()),11)
        self.assertEqual(len(self.packet['levels']),6)
        for l in self.packet['levels']:
            self.assertEqual(set(l['gates']),set(m.GATES))
            self.assertTrue(l['gates']['ORIGINAL_EVIDENCE_COLLECTED'])
            self.assertFalse(l['evidenceComplete'])
            self.assertTrue(all(l['gates'][k] is False for k in m.GATES[3:]))

    def test_sap_dates_separate_cover_reference_and_embedded_claim(self):
        text='Version 1.0 – March 25, 2022\nProtocol Version 3.0 (September 10, 2020)\nSigning Complete Security Checked 3/29/2022 2:58:15 PM\nSYNTHETIC_SIGNER_DO_NOT_EXPORT'
        o=m.sap_observations(text)
        self.assertEqual(o['documentDateUnreviewed'],'2022-03-25')
        self.assertEqual(o['embeddedSigningCompletionDateUnreviewed'],'2022-03-29')
        self.assertEqual(o['referencedProtocolVersionUnreviewed'],'3.0')
        self.assertIsNone(o['approvalEffectiveDate'])
        self.assertNotIn('SYNTHETIC_SIGNER',json.dumps(o))

    def test_missing_embedded_certificate_does_not_invent_signing_date(self):
        o=m.sap_observations('Version 1.0 – March 25, 2022')
        self.assertIsNone(o['embeddedSigningCompletionDateUnreviewed'])
        self.assertIsNone(o['approvalEffectiveDate'])

    def test_after_completion_before_readout_does_not_resolve_prespecification(self):
        c=self.packet['chronologyReconciliation']
        self.assertEqual(c['daysCoverAfterPrimaryCompletion'],92)
        self.assertTrue(c['embeddedSigningBeforePublicTopline'])
        self.assertIsNone(c['databaseLockDate']);self.assertIsNone(c['actualUnblindingDate'])
        self.assertEqual(c['prespecificationConclusion'],'UNRESOLVED');self.assertIsNone(c['postHocConclusion'])

    def test_precompletion_cover_also_cannot_certify_real_unblinding(self):
        o=copy.deepcopy(self.packet['sapObservations']);o['documentDateUnreviewed']='2021-01-01'
        c=m.chronology(o,'4.0','2021-12-23','2022-04-27')
        self.assertEqual(c['prespecificationConclusion'],'UNRESOLVED')
        self.assertIsNone(c['actualUnblindingDate'])

    def test_protocol_reference_mismatch_is_visible_not_silently_reconciled(self):
        self.assertTrue(self.packet['chronologyReconciliation']['protocolReferenceMismatch'])
        self.source('sap-v1')['documentVersion']='2.0'
        with self.assertRaises(ValueError):self.validate()

    def test_database_lock_resolution_cannot_be_caller_supplied(self):
        self.packet['chronologyReconciliation']['databaseLockDate']='2022-03-30'
        with self.assertRaises(ValueError):self.validate()

    def test_effective_approval_and_earlier_sap_uncertainty_remain_explicit(self):
        self.assertEqual(self.packet['chronologyReconciliation']['earlierStandaloneSapVersions'],'UNRESOLVED')
        self.packet['sapObservations']['approvalEffectiveDate']='2022-03-29'
        with self.assertRaises(ValueError):self.validate()

    def test_cross_trial_original_rejected(self):
        self.source('sap-v1')['nct']='NCT05206370'
        with self.assertRaises(ValueError):self.validate()

    def test_wrong_phase_rejected_without_late_phase_imposition(self):
        self.packet['phasesUnreviewed']=['PHASE2']
        with self.assertRaises(ValueError):self.validate()
        prep=m.sibling('level16_research_preparation')
        baseline=json.loads((REPORTS/'focus-source-research-20261114.json').read_text())['trials'][0]['registrySource']
        baseline['phasesUnreviewed']=['PHASE2']
        self.assertTrue(any(x['state']=='NOT_YET_EXPECTED' for x in prep.worksheets(baseline)[2]['requiredEvidence']))

    def test_source_publication_and_utc_retrieval_cutoff_enforced(self):
        source=self.source('primary-report');source['publicationDate']='2026-11-15'
        with self.assertRaises(ValueError):self.validate()
        source['publicationDate']='2023-07-11';source['receipt']['retrievedAt']='2026-11-14T23:00:00-05:00'
        with self.assertRaises(ValueError):self.validate()

    def test_false_owner_completion_gate_rejected(self):
        for gate in m.GATES[3:]:
            with self.subTest(gate=gate):
                self.packet['levels'][0]['gates'][gate]=True
                with self.assertRaises(ValueError):self.validate()
                self.packet['levels'][0]['gates'][gate]=False

    def test_caller_metadata_cannot_fabricate_owner_acceptance(self):
        self.packet['ownerReviewStatus']='OWNER_ACCEPTED_WITH_LIMITATIONS'
        with self.assertRaises(ValueError):self.validate()

    def test_matching_hash_cannot_certify_authentication(self):
        self.source('sap-v1')['receipt']['provenanceIndependentlyAuthenticated']=True
        with self.assertRaises(ValueError):self.validate()

    def test_false_scientific_completion_and_probabilities_rejected(self):
        for field,value in [('assessmentCompleted',True),('evidenceComplete',True),('approvalProbability',0.9),('scientificConclusion','approved')]:
            old=self.packet[field];self.packet[field]=value
            with self.assertRaises(ValueError):self.validate()
            self.packet[field]=old

    def test_application_identity_is_not_promoted_from_provisional_mapping(self):
        self.packet['applicationIdentityVerified']=True;self.packet['applicationCycleId']='achv-cytisinicline'
        with self.assertRaises(ValueError):self.validate()

    def test_outcome_exposure_cannot_be_relabelled_blind(self):
        self.packet['historicalPredictionInputPermitted']=True
        with self.assertRaises(ValueError):self.validate()

    def test_complete_focus_identity_set_required(self):
        self.packet['focusNcts'][-1]='NCT99999999'
        with self.assertRaises(ValueError):self.validate()

    def test_duplicate_or_unbound_source_rejected(self):
        self.packet['sourceInventory'].append(copy.deepcopy(self.source('registry')))
        with self.assertRaises(ValueError):self.validate()
        self.packet['sourceInventory'].pop();self.packet['levels'][0]['factualObservations'][0]['sourceIds']=['invented-source']
        with self.assertRaises(ValueError):self.validate()

    def test_missing_sixth_level_rejected(self):
        self.packet['levels'].pop()
        with self.assertRaises(ValueError):self.validate()

    def test_html_challenge_is_not_pdf_even_if_hash_matches(self):
        raw=b'<html>Preparing to download a public PDF</html>'
        source={'sourceKind':'STATISTICAL_ANALYSIS_PLAN','receipt':self.receipt(raw)}
        with self.assertRaises(ValueError):m.check_original_source(source,raw)

    def test_modified_original_and_wrong_registry_rejected(self):
        raw=b'%PDF-SYNTHETIC_TEST_ONLY';source={'sourceKind':'PROTOCOL','receipt':self.receipt(raw)}
        self.assertIn('NOT_AUTHENTICATED',m.check_original_source(source,raw,'SYNTHETIC ACH-CYT-03'))
        with self.assertRaises(ValueError):m.check_original_source(source,raw,'SYNTHETIC ACH-CYT-04')
        with self.assertRaises(ValueError):m.check_original_source(source,raw+b'modified','SYNTHETIC ACH-CYT-03')
        raw=json.dumps({'protocolSection':{'identificationModule':{'nctId':'NCT05206370'}}}).encode()
        with self.assertRaises(ValueError):m.check_original_source({'sourceKind':'REGISTRY','receipt':self.receipt(raw)},raw)

    def test_offline_preview_shows_dossier_and_escapes_research(self):
        self.packet['levels'][0]['preliminaryInterpretation']='<script>untrusted</script>'
        html=preview.renderer.render(preview.evidence_report(),owner_dossier=self.packet)
        self.assertEqual(html.count('<details>'),32)
        for text in ['Document chronology','Statistical questions','OWNER_REVIEW_COMPLETED','2022-03-29','OWNER_NOT_REVIEWED']:
            self.assertIn(text,html)
        self.assertNotIn('<script>untrusted</script>',html)
        self.assertIn('&lt;script&gt;untrusted&lt;/script&gt;',html)

    def test_queue_preserves_all_remaining_trials_and_unmapped_exceptions(self):
        research=json.loads((REPORTS/'focus-source-research-20261114.json').read_text())
        r=m.prioritize_remaining(research,{'40257755','42148495'})
        self.assertEqual(r['remainingTrialCount'],31)
        self.assertEqual({t['nct'] for t in r['trials']},set(self.ncts)-{m.NCT})
        self.assertEqual(r['nextFive'],['NCT05206370','NCT05813275','NCT03697109','NCT04544293','NCT04716231'])
        self.assertEqual({t['nct'] for t in r['trials'] if t['mappingStatus']=='NOT_MAPPED_APPLICATION_CYCLE'},
            {'NCT05031780','NCT06747468','NCT06553768'})
        self.assertTrue(all(t['approvalProbability'] is None for t in r['trials']))

    def test_owner_research_has_zero_outside_gate(self):
        self.assertFalse(self.packet['externalVerificationRequired'])
        self.assertEqual(self.packet['outsideReviewerCountRequired'],0)
        self.assertTrue(self.packet['ownerCanReviewWithoutExternalVerification'])
        self.packet['externalVerificationRequired']=True
        with self.assertRaises(ValueError):self.validate()

    def test_existing_owner_preview_composes_dossier_without_external_blockers(self):
        module=m.sibling('level16_offline_research_preview')
        read=lambda p:json.loads(p.read_text(encoding='utf-8'))
        html,receipt=module.build(*[read(p) for p in (module.RESEARCH,module.COVERAGE,module.ROSTER,
            module.APPLICATIONS,module.DEFINITIONS,module.ORCA2)],owner_dossier=self.packet)
        self.assertEqual(receipt['focusTrialCount'],32)
        self.assertFalse(receipt['stagingActivated'])
        self.assertIn('OWNER-ONLY RESEARCH — NO EXTERNAL VERIFICATION REQUIRED',html)
        self.assertIn('ORCA-2 OWNER RESEARCH',html)
        self.assertNotIn('Gate blockers:',html)
        self.assertNotIn('Independent review checklist',html)

    def test_existing_publication_and_chronology_checks_are_reused(self):
        original=m.sibling
        calls=[]
        def tracked(name):calls.append(name);return original(name)
        from unittest.mock import patch
        with patch.object(m,'sibling',side_effect=tracked):self.validate()
        for name in ['level1_20_owner_policy','level16_orca2_statistical_timeline','level16_orca2_publication_review']:
            self.assertIn(name,calls)

    def test_primary_and_posthoc_fulltext_correction_is_explicit(self):
        self.assertTrue(any('overstated' in x for x in self.packet['unresolvedDiscrepancies']))
        self.assertEqual(self.source('primary-report')['sourceKind'],'PRIMARY_TRIAL_REPORT_HTML')
        excluded=[x for x in self.packet['sourceSearchAttempts'] if 'journal-supplement' in x['id']]
        self.assertTrue(all(x['researchUse']=='HTML_SHELL_OR_CHALLENGE_NOT_ORIGINAL_REQUESTED_DOCUMENT' for x in excluded))


if __name__=='__main__':unittest.main()
