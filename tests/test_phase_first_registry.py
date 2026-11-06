"""Identity/chronology and resumability checks for phase-first collection."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collect_phase_first_registry_20261106 import project
from collect_company_phase_first import collect

class PhaseFirstRegistryTests(unittest.TestCase):
    def study(self):
        return {'protocolSection':{'identificationModule':{'nctId':'NCT00000001','briefTitle':'Fixture'},
            'statusModule':{'overallStatus':'RECRUITING','lastUpdatePostDateStruct':{'date':'2026-11-01'}},
            'designModule':{'phases':['PHASE1','PHASE2'],'studyType':'INTERVENTIONAL'},
            'sponsorCollaboratorsModule':{'leadSponsor':{'name':'Fixture'}}}}
    def test_exact_identity_and_phase(self):
        r=project(self.study(),'2026-11-06T00:00:00Z','https://clinicaltrials.gov/api/v2/studies/NCT00000001',{'NCT00000001'})
        self.assertEqual(r['phases'],['PHASE1','PHASE2'])
        self.assertEqual(r['hasResults'],False)
        self.assertEqual(len(r['sourceSha256']),64)
        with self.assertRaisesRegex(ValueError,'UNREQUESTED_NCT'):
            project(self.study(),'2026-11-06T00:00:00Z','https://example.org',{'NCT00000002'})
    def test_future_snapshot_rejected(self):
        with self.assertRaisesRegex(ValueError,'FUTURE_SOURCE_DATE'):
            project(self.study(),'2026-10-01T00:00:00Z','https://example.org')
    def test_unknown_company_cannot_expand_census(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'UNKNOWN_TICKER'):
                collect('NOT_A_CENSUS_COMPANY',Path(temp),Path(temp)/'output.json')

if __name__=='__main__':unittest.main()
