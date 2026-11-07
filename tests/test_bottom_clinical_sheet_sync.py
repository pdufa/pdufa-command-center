import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('sync_ratings',Path(__file__).resolve().parents[1]/'scripts/sync_bottom_clinical_ratings.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BottomSheetSyncTests(unittest.TestCase):
    def fixture(self):
        header=['']*28
        for i,title in m.EXPECTED.items():header[i]=title
        row=['']*28;row[0]='TEST';row[1]='NCT00000001';row[15]='EXISTING VALIDATED VALUE';row[20]='KEEP RESEARCH NOTE'
        rating={'nctId':row[1],'ticker':'TEST','clinicalFullScore':None,'asOf':'2026-11-07','evidenceNote':'Exact-NCT sources retained','factors':[{'id':'post-1-'+str(i),'grade':None if i==5 else 75,'state':'NOT_REPORTED'} for i in range(1,6)]}
        return [header,row],rating
    def test_only_exact_nct_active_rows_written(self):
        rows,r=self.fixture();other={**r,'nctId':'NCT00000002'}
        plan=m.build_plan(rows,[r,other]);self.assertEqual({c['nctId'] for c in plan},{r['nctId']})
        self.assertEqual({c['column'] for c in plan},{12,16,17,18})
        self.assertEqual(rows[1][15],'EXISTING VALIDATED VALUE');self.assertEqual(rows[1][20],'KEEP RESEARCH NOTE')
    def test_partial_score_cannot_be_written_as_combined(self):
        rows,r=self.fixture();r['clinicalFullScore']=75
        with self.assertRaisesRegex(ValueError,'INVALID_COMBINED_SCORE'):m.build_plan(rows,[r])
    def test_company_ticker_matching_does_not_replace_nct_matching(self):
        rows,r=self.fixture();r['nctId']='NCT00000002';self.assertEqual(m.build_plan(rows,[r]),[])
    def test_duplicates_rejected(self):
        rows,r=self.fixture();rows.append(rows[1])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_EXACT_NCT'):m.build_plan(rows,[r])
    def test_previous_value_and_notes_preserved_in_each_update(self):
        rows,r=self.fixture();plan=m.build_plan(rows,[r]);requests=m.batch_requests(plan,202611061,{(3,12):'Existing audit observation'})
        first=requests[0]['updateCells'];cell=first['rows'][0]['values'][0]
        self.assertIn('Existing audit observation',cell['note']);self.assertIn('Prior value',cell['note']);self.assertEqual(first['fields'],'userEnteredValue,note,userEnteredFormat.wrapStrategy')
    def test_zero_write_recheck_keeps_prior_sync_audit(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);first={'writes':18,'verified':True};second={'writes':0,'verified':True}
            m.persist_receipt(directory,first);m.persist_receipt(directory,second);m.persist_receipt(directory,second)
            self.assertEqual(json.loads((directory/'sheets-sync-history.json').read_text())['runs'],[first,second])
            self.assertEqual(json.loads((directory/'sheets-sync-receipt.json').read_text()),second)
if __name__=='__main__':unittest.main()
