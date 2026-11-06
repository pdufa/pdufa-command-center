"""Exact identity and chronology guards for the public registry collector."""
import unittest
from scripts.recover_phase3_population_geography import project

class PopulationRecoveryTests(unittest.TestCase):
    def study(self):
        return {'protocolSection':{
            'identificationModule':{'nctId':'NCT05139810','orgStudyIdInfo':{'id':'ISIS 721744-CS5'}},
            'statusModule':{'lastUpdatePostDateStruct':{'date':'2025-02-13'}},
            'eligibilityModule':{'minimumAge':'12 Years','sex':'ALL','healthyVolunteers':False},
            'contactsLocationsModule':{'locations':[{'country':'United States'},{'country':'France'}]}}}

    def test_no_cross_trial_identity_in_batch(self):
        with self.assertRaisesRegex(ValueError,'UNREQUESTED_NCT'):
            project(self.study(),{'NCT04568434'},'2026-11-06T12:00:00Z','a'*64)

    def test_missing_or_future_source_publication_cannot_be_replaced_by_retrieval_date(self):
        x=self.study()
        x['protocolSection']['statusModule']={}
        with self.assertRaisesRegex(ValueError,'PUBLICATION_DATE_UNAVAILABLE'):
            project(x,{'NCT05139810'},'2026-11-06T12:00:00Z','a'*64)
        x['protocolSection']['statusModule']={'lastUpdatePostDateStruct':{'date':'2026-11-07'}}
        with self.assertRaisesRegex(ValueError,'FUTURE_REGISTRY'):
            project(x,{'NCT05139810'},'2026-11-06T12:00:00Z','a'*64)

    def test_registered_design_never_becomes_results_or_forecasts(self):
        x=self.study()
        x['hasResults']=True
        x['resultsSection']={'outcomeMeasuresModule':{'outcomeMeasures':[{'pValue':'0.001'}]}}
        r=project(x,{'NCT05139810'},'2026-11-06T12:00:00Z','a'*64)
        self.assertEqual(r['publicationDate'],'2025-02-13')
        self.assertEqual(r['registeredLocationCount'],2)
        self.assertEqual(r['criticalReviewStatus'],'NOT_YET_REVIEWED')
        self.assertNotIn('score',r)
        self.assertNotIn('endpointOutcome',r)
        self.assertNotIn('pdufaGoalDate',r)

if __name__=='__main__':
    unittest.main()
