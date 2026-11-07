import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('bottom_backfill',Path(__file__).resolve().parents[1]/'scripts/bottom_only_evidence_backfill.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BottomBackfillTests(unittest.TestCase):
    def document(self, nct='NCT00000001', phase='PHASE3'):
        return {'protocolSection':{'identificationModule':{'nctId':nct},'designModule':{'phases':[phase]},'statusModule':{'overallStatus':'ACTIVE_NOT_RECRUITING'}}}
    def test_exact_identity_required(self):
        with self.assertRaisesRegex(ValueError,'EXACT_NCT_MISMATCH'):m.extract('NCT00000002',self.document())
    def test_non_phase3_rejected(self):
        with self.assertRaisesRegex(ValueError,'PHASE3_MISMATCH'):m.extract('NCT00000001',self.document(phase='PHASE2'))
    def test_missing_registry_results_do_not_create_negative_results_or_scores(self):
        facts,review=m.extract('NCT00000001',self.document())
        self.assertFalse(review['resultsAvailable']);self.assertIsNone(review['reportedResults'])
        self.assertFalse(any('grade' in fact or fact['question']==23 for fact in facts))
    def test_unposted_secondary_is_not_a_sourced_result(self):
        doc=self.document();doc['resultsSection']={'outcomeMeasuresModule':{'outcomeMeasures':[{'type':'SECONDARY','reportingStatus':'NOT_POSTED','title':'Future endpoint'}]}}
        facts,review=m.extract('NCT00000001',doc)
        self.assertFalse(any(f['question']==17 for f in facts))
    def test_administrative_refresh_preserves_clinical_hash(self):
        import copy
        original=self.document();updated=copy.deepcopy(original)
        updated['protocolSection']['statusModule']['lastUpdatePostDateStruct']={'date':'2026-11-07'}
        self.assertEqual(m.clinical_fingerprint(original),m.clinical_fingerprint(updated))
        updated['resultsSection']={'outcomeMeasuresModule':{'outcomeMeasures':[{'title':'Changed clinical result'}]}}
        self.assertNotEqual(m.clinical_fingerprint(original),m.clinical_fingerprint(updated))
    def test_active_intake_appends_without_removing_historical_identity(self):
        historical={'nctId':'NCT00000002','notes':'Retain original audit'}
        baseline={'records':[historical]};matrix={'headers':['']*190,'rows':[['history']+['']*189]}
        active={'asOf':'2026-11-07','records':[{'nct':'NCT00000001','ticker':'TEST','company':'Test','marketCap':500000000,'resultsUrl':'https://clinicaltrials.gov/study/NCT00000001','fdaStatus':'Pending'}]}
        added=m.reconcile_active_inventory(baseline,matrix,active,{'NCT00000001':self.document()})
        self.assertEqual(len(added),1);self.assertEqual(baseline['records'][0],historical)
        self.assertEqual(matrix['rows'][0][0],'history');self.assertEqual(len(matrix['rows'][1]),190)
        self.assertFalse(added[0]['classificationVerified'])
        self.assertEqual(m.reconcile_active_inventory(baseline,matrix,active,{}),[])
if __name__=='__main__':unittest.main()
