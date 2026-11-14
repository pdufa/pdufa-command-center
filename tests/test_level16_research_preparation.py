"""Offline synthetic acquisition/worksheet tests; no clinical signoff or live calls."""
import copy
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/medical'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

m=load('level16_research_preparation');preview=load('render_level16_focus_preview')


def packet(nct,phases=None,**changes):
    result={'protocolSection':{'identificationModule':{'nctId':nct},'statusModule':{
        'lastUpdatePostDateStruct':{'date':'2026-11-10'},'overallStatus':'RECRUITING'},
        'designModule':{'phases':phases or ['PHASE2'],'enrollmentInfo':{'count':20,'type':'ESTIMATED'},
                        'designInfo':{'allocation':'RANDOMIZED','maskingInfo':{'masking':'DOUBLE'}}},
        'conditionsModule':{'conditions':['SYNTHETIC_TEST_ONLY_CONDITION']},
        'outcomesModule':{'primaryOutcomes':[{'measure':'<script>untrusted endpoint</script>','timeFrame':'Week 12'}]}},
        'hasResults':False,'documentSection':{'largeDocumentModule':{'largeDocs':[
            {'filename':'Prot_000.pdf','hasProtocol':True,'hasSap':False,'date':'2026-10-01'}]}}}
    result.update(changes);return json.dumps(result).encode()


class Response:
    def __init__(self,url,data):self.url,self.data=url,data
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def geturl(self):return self.url
    def read(self,limit):return self.data[:limit]


class ResearchPreparationTests(unittest.TestCase):
    def setUp(self):
        self.roster=json.loads(m.ROSTER.read_text());self.apps=json.loads(m.APPLICATIONS.read_text())
        self.nct=self.roster['records'][0]['nct'];self.now=datetime(2026,11,13,12,tzinfo=timezone.utc)
        self.receipt=m.extract(packet(self.nct),self.nct,self.now.isoformat(),'2026-11-13')

    def report(self):return m.build(self.roster,self.apps,{self.nct:self.receipt},'2026-11-13')

    def test_all_32_records_six_worksheets_and_unmapped_exceptions_preserved(self):
        r=self.report();m.validate_snapshot(r,[t['nct'] for t in self.roster['records']])
        self.assertEqual((r['focusTrialCount'],r['mappedTrialCount'],r['provisionalApplicationCycleCount'],r['unmappedTrialCount']),(32,29,23,3))
        self.assertEqual({t['nct'] for t in r['trials'] if t['mappingStatus']=='NOT_MAPPED_APPLICATION_CYCLE'},
                         {'NCT05031780','NCT06747468','NCT06553768'})
        self.assertEqual(r['trialsWithPreliminaryResearchFindings'],1)
        self.assertTrue(all(len(t['levels'])==6 for t in r['trials']))
        self.assertEqual(r['actualAuthenticatedSources'],0);self.assertEqual(r['actualIndependentAssessments'],0)

    def test_committed_public_snapshot_is_complete_unreviewed_and_not_prediction_input(self):
        snapshot=json.loads((ROOT/'reports/scientific-levels1-6/focus-source-research-20261113.json').read_text(encoding='utf-8'))
        m.validate_snapshot(snapshot,[t['nct'] for t in self.roster['records']])
        self.assertEqual(snapshot['trialsWithRetrievedRegistry'],32)
        self.assertEqual(snapshot['trialsWithPreliminaryResearchFindings'],32)
        self.assertEqual(snapshot['retrievedOriginalDocumentCount'],34)
        self.assertFalse(snapshot['historicalPredictionInputPermitted'])
        self.assertTrue(all(t['registrySource']['provenanceIndependentlyAuthenticated'] is False for t in snapshot['trials']))

    def test_actual_phase_changes_questions_without_future_phase3_requirements(self):
        for phases in (['PHASE1'],['PHASE2'],['PHASE2','PHASE3'],['PHASE3'],['PHASE4'],['NA']):
            source=m.extract(packet(self.nct,phases),self.nct,self.now.isoformat(),'2026-11-13')
            for item in m.worksheets(source):
                future=[v for v in item['requiredEvidence'] if v['requirement']=='future_phase3_confirmatory_package']
                expected=phases in (['PHASE1'],['PHASE2']) and item['level'] in (3,5)
                self.assertEqual(bool(future),expected)
                self.assertTrue(item['questions']);self.assertTrue(item['abstainWhen'])

    def test_wrong_nct_and_cutoff_rejected(self):
        with self.assertRaises(ValueError):m.extract(packet('NCT99999999'),self.nct,self.now.isoformat(),'2026-11-13')
        with self.assertRaises(ValueError):m.extract(packet(self.nct),self.nct,'2026-11-14T00:00:00+00:00','2026-11-13')
        with self.assertRaises(ValueError):m.extract(packet(self.nct),self.nct,'2026-11-13T23:00:00-05:00','2026-11-13')
        with self.assertRaises(ValueError):m.extract(packet(self.nct),self.nct,'2026-11-13T12:00:00','2026-11-13')
        with self.assertRaises(ValueError):m.extract(packet(self.nct),self.nct,self.now.isoformat(),'2026-11-09')

    def test_original_bytes_are_content_addressed_and_never_overwritten(self):
        raw=packet(self.nct)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            opener=lambda request,timeout:Response(request.full_url,raw)
            first=m.acquire(self.nct,root,'2026-11-13',opener,self.now)
            again=m.acquire(self.nct,root,'2026-11-13',opener,self.now)
            self.assertEqual(first,again)
            path=root/'registry'/self.nct/(first['documentSha256']+'.json')
            self.assertEqual(path.read_bytes(),raw)
            path.write_bytes(b'modified synthetic evidence')
            with self.assertRaises(ValueError):m.acquire(self.nct,root,'2026-11-13',opener,self.now)
            self.assertEqual(path.read_bytes(),b'modified synthetic evidence')
        with self.assertRaises(ValueError):m.acquire(self.nct,ROOT/'do-not-write','2026-11-13',opener,self.now)

    def test_redirect_and_oversize_sources_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):m.acquire(self.nct,root,'2026-11-13',lambda request,timeout:Response('https://wrong.example.test',packet(self.nct)),self.now)
        with self.assertRaises(ValueError):m.extract(b'x'*(m.MAX_BYTES+1),self.nct,self.now.isoformat(),'2026-11-13')

    def test_public_original_pdf_retrieval_never_authenticates_document(self):
        lead=self.receipt['sourceLeads'][0]
        with tempfile.TemporaryDirectory() as root:
            receipt=m.acquire_registry_document(lead,self.nct,root,'2026-11-13',lambda request,timeout:Response(request.full_url,b'%PDF-1.7 SYNTHETIC ONLY'),self.now)
            self.assertEqual(receipt['state'],'HASH_CHECKED')
            self.assertFalse(receipt['provenanceIndependentlyAuthenticated'])
            self.assertIsNone(receipt['publicationDate']);self.assertIsNone(receipt['protocolVersion'])
            with self.assertRaises(ValueError):m.acquire_registry_document(dict(lead,url='https://evil.example.test/file.pdf'),self.nct,root,'2026-11-13')

    def test_reported_primary_values_are_literal_quotes_not_success_or_probabilities(self):
        outcome={'type':'PRIMARY','title':'SYNTHETIC_TEST_ONLY_ENDPOINT','units':'percent',
                 'groups':[{'id':'OG001','title':'Synthetic group'}],
                 'classes':[{'categories':[{'measurements':[{'groupId':'OG001','value':'12.3'}]}]}],
                 'analyses':[{'groupIds':['OG001'],'pValue':'0.08'}]}
        raw=packet(self.nct,hasResults=True,resultsSection={'outcomeMeasuresModule':{'outcomeMeasures':[outcome]}})
        source=m.extract(raw,self.nct,self.now.isoformat(),'2026-11-13')
        self.assertEqual(source['primaryResultsUnreviewed'][0]['reportedFields']['analyses'][0]['pValue'],'0.08')
        self.assertEqual(source['primaryResultsUnreviewed'][0]['reportedFields']['classes'],outcome['classes'])
        for level in (3,5):
            item=m.worksheets(source)[level-1]
            self.assertTrue(any(f['locator'].startswith('resultsSection.outcomeMeasuresModule') for f in item['preliminaryFindings']))
            self.assertIsNone(item['scientificConclusion']);self.assertIsNone(item['approvalProbability'])
            self.assertFalse(item['assessmentCompleted'])

    def test_unknown_result_group_ids_require_reconciliation_not_inferred_comparators(self):
        raw=packet(self.nct,hasResults=True,resultsSection={'outcomeMeasuresModule':{'outcomeMeasures':[{
            'type':'PRIMARY','groups':[{'id':'OG001','title':'Synthetic group'}],
            'analyses':[{'groupIds':['NOT_REGISTERED'],'pValue':'0.0001'}]}]}})
        source=m.extract(raw,self.nct,self.now.isoformat(),'2026-11-13')
        self.assertIn('RESULT_GROUP_ID_RECONCILIATION_REQUIRED',source['contradictionLeads'])
        self.assertEqual(source['primaryResultsUnreviewed'][0]['groupIdentityStatus'],'UNRESOLVED_RECONCILIATION_REQUIRED')
        self.assertFalse(m.worksheets(source)[2]['assessmentCompleted'])

    def test_results_posting_is_not_efficacy_or_trial_success(self):
        self.assertIsNone(m.worksheets(self.receipt)[2]['scientificConclusion'])
        source=m.extract(packet(self.nct,hasResults=True),self.nct,self.now.isoformat(),'2026-11-13')
        self.assertIn('REGISTRY_RESULTS_FLAG_WITHOUT_RESULTS_CONTENT',source['contradictionLeads'])
        self.assertFalse(source['registryResultsContentPresent'])
        self.assertFalse(m.worksheets(source)[2]['assessmentCompleted'])

    def test_no_forged_independent_review_probability_or_historical_claim(self):
        for key,value in (('actualAuthenticatedSources',1),('actualIndependentAssessments',1),
                          ('prospectiveBlindAssessment',True),('historicalPredictionInputPermitted',True)):
            r=self.report();r[key]=value
            with self.assertRaises(ValueError):m.validate_snapshot(r,[t['nct'] for t in self.roster['records']])
        for key,value in (('score',50),('approvalProbability',0.9),('assessmentCompleted',True)):
            r=self.report();r['trials'][0]['levels'][0][key]=value
            with self.assertRaises(ValueError):m.validate_snapshot(r,[t['nct'] for t in self.roster['records']])

    def test_cross_evidence_findings_and_company_application_mismatch_rejected(self):
        r=self.report();r['trials'][0]['levels'][0]['preliminaryFindings'][0]['documentSha256']='f'*64
        with self.assertRaises(ValueError):m.validate_snapshot(r,[t['nct'] for t in self.roster['records']])
        apps=copy.deepcopy(self.apps);apps['records'][0]['candidateApplications'][0]['ticker']='WRONG'
        with self.assertRaises(ValueError):m.build(self.roster,apps,{self.nct:self.receipt},'2026-11-13')

    def test_preview_escapes_preliminary_data_and_does_not_promote_review(self):
        research=self.report()
        engine=load('phase_first_levels_1_6');definition=json.loads(engine.DEFINITION_PATH.read_text())
        readiness=m.readiness_report(research,self.roster,self.apps,definition)
        html=preview.render(readiness,preliminary_research=research)
        self.assertIn('PRELIMINARY RESEARCH',html);self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html);self.assertIn('NOT ADJUDICATED',html)
        self.assertEqual(readiness['scientificallyAdjudicatedLevels'],0)
        self.assertTrue(all(l['approvalProbability'] is None for t in readiness['trials'] for l in t['levels']))


if __name__=='__main__':unittest.main()
