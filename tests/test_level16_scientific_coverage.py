"""Offline coverage integrity tests; synthetic fixtures cannot authorize reviews."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coverage_report', ROOT/'scripts/medical/level16_scientific_coverage.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
REPORTS = ROOT/'reports/scientific-levels1-6'


class ScientificCoverageTests(unittest.TestCase):
    def setUp(self):
        self.research = json.loads((REPORTS/'focus-source-research-20261114.json').read_text(encoding='utf-8'))
        self.ncts = {x['nct'] for x in self.research['trials']}

    def receipt(self, raw):
        return {'state':'HASH_CHECKED','documentSha256':hashlib.sha256(raw).hexdigest(),'byteCount':len(raw),
            'retrievedAt':'2026-11-14T00:00:00+00:00','evidenceCutoffDate':'2026-11-14',
            'provenanceIndependentlyAuthenticated':False,'independentlyScientificallyReviewed':False,
            'sourceUrl':'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=1'}

    def xml(self, date_xml='<Year>2026</Year><Month>Nov</Month><Day>13</Day>'):
        return ('<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article>'
            '<ArticleTitle>SYNTHETIC TEST ONLY</ArticleTitle><Journal><JournalIssue><PubDate>'+date_xml+
            '</PubDate></JournalIssue></Journal><DataBankList><DataBank><AccessionNumberList>'
            '<AccessionNumber>NCT99999999</AccessionNumber></AccessionNumberList></DataBank></DataBankList>'
            '</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>').encode()

    def test_complete_roster_and_provisional_crosswalk_preserved(self):
        r = m.coverage(self.research)
        self.assertEqual(r['focusTrialCount'],32)
        self.assertEqual(self.research['mappedTrialCount'],29)
        self.assertEqual(self.research['provisionalApplicationCycleCount'],23)
        self.assertEqual({x['nct'] for x in r['trials'] if x['mappingStatus']=='NOT_MAPPED_APPLICATION_CYCLE'},
            {'NCT05031780','NCT06747468','NCT06553768'})

    def test_coverage_recomputes_from_collected_receipts(self):
        r = m.coverage(self.research)
        self.assertEqual(r['trialCoverageCounts'],{'registry':32,'protocol':12,'sap':12,'postedResults':12,
            'indexedJournalRecords':15,'retrievedPublicFullTexts':10,'exactNctFdaLabelPackets':2})
        self.assertEqual(r['uniqueRegistryAndProtocolSapOriginals'],55)
        self.assertEqual(r['trialsWithSixPreliminaryLevels'],32)
        saved=json.loads((REPORTS/'scientific-coverage-20261114.json').read_text())
        for key,value in r.items(): self.assertEqual(value,saved[key],key)

    def test_six_separate_levels_show_research_evidence_and_abstention(self):
        for trial in self.research['trials']:
            self.assertEqual([x['level'] for x in trial['levels']],list(range(1,7)))
            for level in trial['levels']:
                for field in ('evidenceActuallyCollected','preliminaryFindings','preliminaryResearchInterpretation',
                    'supportingReasons','riskFactorsRequiringReview','missingEvidence','scientificReviewRequirements','abstainWhen'):
                    self.assertTrue(level[field],(trial['nct'],field))
                self.assertEqual(level['independentReviewStatus'],'NOT_ADJUDICATED')

    def test_receipt_requires_original_bytes_and_correct_digest(self):
        raw=self.xml();receipt=self.receipt(raw)
        m.verify_receipt(receipt,'2026-11-14',raw)
        with self.assertRaises(ValueError):m.verify_receipt(receipt,'2026-11-14',raw+b'modified')
        receipt['byteCount']+=1
        with self.assertRaises(ValueError):m.verify_receipt(receipt,'2026-11-14',raw)

    def test_checksum_does_not_allow_authentication_claim(self):
        raw=self.xml();receipt=self.receipt(raw);receipt['provenanceIndependentlyAuthenticated']=True
        with self.assertRaises(ValueError):m.publication_records(raw,receipt,'2026-11-14')

    def test_retrieval_cutoff_and_timezone_enforced(self):
        raw=self.xml()
        for timestamp in ('2026-11-15T00:00:00+00:00','2026-11-14T23:30:00-05:00','2026-11-14T00:00:00'):
            rec=self.receipt(raw);rec['retrievedAt']=timestamp
            with self.assertRaises(ValueError):m.verify_receipt(rec,'2026-11-14',raw)

    def test_future_and_imprecise_publication_not_counted(self):
        for date_xml in ('<Year>2026</Year><Month>Nov</Month><Day>15</Day>', '<Year>2026</Year><Month>Nov</Month>'):
            raw=self.xml(date_xml);result=m.publication_records(raw,self.receipt(raw),'2026-11-14')['1']
            self.assertFalse(result['inCutoff'])
            self.assertEqual(result['relationshipStatus'],'INDEXED_NCT_LINK_ONLY_NOT_VERIFIED_TRIAL_REPORT')

    def test_publication_exact_date_and_no_abstract_body_export(self):
        raw=self.xml();p=m.publication_records(raw,self.receipt(raw),'2026-11-14')['1']
        self.assertEqual(p['publicationDate'],'2026-11-13');self.assertTrue(p['inCutoff'])
        self.assertNotIn('abstract',p);self.assertIsNone(p['fullTextReceipt'])

    def test_duplicate_publication_identity_rejected(self):
        raw=self.xml();node=raw.split(b'<PubmedArticleSet>')[1].split(b'</PubmedArticleSet>')[0]
        raw=b'<PubmedArticleSet>'+node+node+b'</PubmedArticleSet>'
        with self.assertRaises(ValueError):m.publication_records(raw,self.receipt(raw),'2026-11-14')

    def test_cross_trial_document_substitution_rejected(self):
        trial=self.research['trials'][0];receipt=copy.deepcopy(trial['additionalOriginalDocuments'][0]);receipt['nct']='NCT99999999'
        with self.assertRaises(ValueError):m.enrich(self.research,[{'nct':trial['nct'],'receipt':receipt}],{})

    def test_duplicate_document_receipt_rejected(self):
        trial=self.research['trials'][0];row={'nct':trial['nct'],'receipt':trial['additionalOriginalDocuments'][0]}
        with self.assertRaises(ValueError):m.enrich(self.research,[row,row],{})

    def test_modified_saved_publication_cutoff_rejected(self):
        trial=next(t for t in self.research['trials'] if t['publicationResearch'])
        trial['publicationResearch'][0]['inCutoff']=False
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_cross_publication_fulltext_substitution_rejected(self):
        publication=next(p for t in self.research['trials'] for p in t['publicationResearch'] if p.get('fullTextReceipt'))
        publication['fullTextReceipt']['boundPmidUnreviewed']='99999999'
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_cross_trial_publication_substitution_rejected(self):
        trial=self.research['trials'][0]
        trial['publicationResearch']=[copy.deepcopy(next(p for t in self.research['trials'] for p in t['publicationResearch']))]
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_no_authentication_adjudication_or_probabilities_fabricated(self):
        r=m.coverage(self.research)
        for key in ('independentlyAuthenticatedSources','independentlyAdjudicatedAssessments','verifiedPeerReviewedTrialReports','verifiedExactTrialFdaDocuments'):
            self.assertEqual(r[key],0)
        self.assertIsNone(r['approvalProbability']);self.assertFalse(r['historicalPredictionInputPermitted'])
        self.research['trials'][0]['levels'][0]['approvalProbability']=0.7
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_distinct_endpoint_findings_and_not_blanket_success(self):
        trial=next(t for t in self.research['trials'] if t['nct']=='NCT05031780')
        observation=trial['levels'][2]['publicLiteratureObservationUnreviewed']
        self.assertIn('p=0.1213',observation['factualObservation'])
        self.assertIn('does not establish',observation['preliminaryInterpretation'])
        self.assertTrue(trial['levels'][2]['contradictoryFindings'])
        self.assertIsNone(trial['levels'][2]['scientificConclusion'])

    def test_missing_and_nonpublic_and_future_phase_remain_distinct(self):
        for t in self.research['trials']:
            for l in t['levels']:
                self.assertEqual(l['nonpublicEvidence'],[])
                self.assertIn('NOT_ESTABLISHED',l['nonpublicAvailabilityStatus'])
        source=copy.deepcopy(self.research['trials'][0]['registrySource']);source['phasesUnreviewed']=['PHASE2']
        levels=m.preparation().worksheets(source)
        self.assertTrue(any(x['state']=='NOT_YET_EXPECTED' for x in levels[2]['requiredEvidence']))

    def test_all_owner_decisions_remain_unapproved_and_actionable(self):
        resolution=json.loads((REPORTS/'owner-approval-resolution-20261114.json').read_text())
        config=json.loads((ROOT/'infra/level16-staging/owner-approval.json').read_text())
        self.assertEqual([x['id'] for x in resolution['decisions']],['A%02d'%i for i in range(1,15)])
        self.assertFalse(config['liveAccessEnabled']);self.assertFalse(resolution['liveAccessEnabled'])
        for row in resolution['decisions']:
            self.assertNotEqual(row['status'],'VERIFIED_APPROVED');self.assertIsNone(row['approvalReference'])
            for key in ('realWorldInformationStillNeeded','minimumOwnerAction','freeAndPaidAlternatives','establishedInformation'):
                self.assertTrue(row[key])

    def test_unmapped_research_cannot_become_crosswalk(self):
        r=json.loads((REPORTS/'unmapped-application-research-20261114.json').read_text())
        self.assertEqual(r['mappingChanges'],0);self.assertEqual(r['independentlyVerifiedRelationships'],0)
        self.assertEqual({t['nct'] for t in r['trials']},{'NCT05031780','NCT06747468','NCT06553768'})
        for t in r['trials']:
            self.assertEqual(t['relationshipStatus'],'NOT_MAPPED_APPLICATION_CYCLE')
            self.assertFalse(t['independentlyReviewed'])

    def test_read_only_report_does_not_rewrite_previous_snapshot(self):
        old=REPORTS/'focus-source-research-20261113.json';before=old.read_bytes()
        m.coverage(self.research);self.assertEqual(old.read_bytes(),before)

    def test_fda_cross_trial_search_or_verification_claim_rejected(self):
        trial=next(t for t in self.research['trials'] if t['fdaExactNctSearch'].get('labelMatchesUnreviewed'))
        trial['fdaExactNctSearch']['nct']='NCT99999999'
        with self.assertRaises(ValueError):m.coverage(self.research)
        trial['fdaExactNctSearch']['nct']=trial['nct']
        trial['fdaExactNctSearch']['relationshipVerified']=True
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_future_fda_label_excluded(self):
        trial=next(t for t in self.research['trials'] if t['fdaExactNctSearch'].get('labelMatchesUnreviewed'))
        trial['fdaExactNctSearch']['labelMatchesUnreviewed'][0]['effectiveTime']='20261115'
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_declared_future_original_document_excluded(self):
        self.research['trials'][0]['additionalOriginalDocuments'][0]['registryDeclaredDocumentDateUnreviewed']='2026-11-15'
        with self.assertRaises(ValueError):m.coverage(self.research)

    def test_research_display_escapes_new_interpretations_and_stays_unreviewed(self):
        spec=importlib.util.spec_from_file_location('preview',ROOT/'tests/test_render_level16_focus_preview.py')
        preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
        self.research['trials'][0]['levels'][0]['preliminaryResearchInterpretation']='<script>research</script>'
        html=preview.renderer.render(preview.evidence_report(),preliminary_research=self.research)
        self.assertNotIn('<script>research</script>',html)
        self.assertIn('&lt;script&gt;research&lt;/script&gt;',html)
        self.assertIn('PRELIMINARY RESEARCH',html)
        self.assertEqual(html.count('<details>'),32)


if __name__=='__main__':unittest.main()
