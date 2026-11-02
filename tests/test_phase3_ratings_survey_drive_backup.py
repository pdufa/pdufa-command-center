"""Source identity and 20-rating/38-ingredient Google backup regression tests."""
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"scripts/sync_phase3_ratings_survey_to_google_drive.py"
spec=importlib.util.spec_from_file_location("phase3_drive_ratings",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RatingsBackUpTests(unittest.TestCase):
    def setUp(self):
        self.source=m.read_json(m.TRIALS)
        self.tax=m.read_json(m.TAXONOMY)
        self.saved=m.read_json(m.SAVED)
    def test_all_registry_ncts_have_20_rating_records_and_38_ingredient_questions(self):
        tabs,counts=m.prepare(self.source,self.tax,self.saved,[])
        n=self.source["total"]
        self.assertEqual(counts["trials"],n)
        self.assertEqual(len(tabs[m.SUMMARY]),n+1)
        self.assertEqual(len(tabs[m.SURVEY]),20*n+1)
        self.assertEqual(len(tabs[m.INGREDIENTS]),39)
        self.assertEqual(counts["sourcedIngredientObservations"],0)
        self.assertEqual(set(x[1] for x in tabs[m.SUMMARY][1:]),
            set(x["nctId"] for x in self.source["records"]))
        self.assertEqual(len({(x[0],x[3]) for x in tabs[m.SURVEY][1:]}),20*n)
        self.assertTrue(all(x[12]=="" for x in tabs[m.SURVEY][1:]))
        self.assertTrue(all(x[13]=="NOT_ASSESSED" for x in tabs[m.SURVEY][1:]))
    def test_verified_exact_nct_field_is_sourced_but_not_scored(self):
        trial=self.source["records"][0];nct=trial["nctId"]
        groups=self.tax["assessments"]
        f=groups[0]["ingredients"][0]["id"]
        canonical=[{"nctId":nct,"ticker":trial["ticker"],"drug":"Source drug",
            "indication":"Source disease","assessments":[
                {"rank":g["rank"],"title":g["name"],"inputs":[
                    {"id":x["id"],"state":"VERIFIED" if x["id"]==f else "MISSING",
                     "sourceUrl":"https://clinicaltrials.gov/study/"+nct if x["id"]==f else None,
                     "sourceDate":"2026-10-01" if x["id"]==f else None,
                     "value":"Observed" if x["id"]==f else "Not assessed",
                     "method":"verified source extraction","confidence":"MODERATE"}
                    for x in g["ingredients"]]} for g in groups]}]
        tabs,counts=m.prepare(self.source,self.tax,self.saved,canonical)
        self.assertEqual(counts["exactCanonicalMatched"],1)
        self.assertEqual(counts["sourcedIngredientObservations"],1)
        rating=[r for r in tabs[m.SURVEY][1:] if r[0]==nct and r[3]==1][0]
        self.assertEqual(rating[8:12],[1,0,1,2])
        self.assertEqual(rating[12],"")
        self.assertEqual(rating[13],"PARTIAL_INPUTS_NOT_SCORED")
        self.assertIn("https://clinicaltrials.gov",rating[15])
    def test_mismatched_ticker_never_imports_canonical_score(self):
        item=self.source["records"][0]
        rec={"nctId":item["nctId"],"ticker":"WRONG",
             "assessments":[{"rank":g["rank"],"title":g["name"],"inputs":[]}
                            for g in self.tax["assessments"]]}
        # No verified program identity, so the record cannot contribute ratings.
        tabs,counts=m.prepare(self.source,self.tax,self.saved,[rec])
        self.assertEqual(counts["exactCanonicalMatched"],0)
        self.assertEqual(counts["sourcedIngredientObservations"],0)
    def test_duplicate_nct_raises(self):
        d=dict(self.source);d["records"]=list(self.source["records"])
        d["records"][1]=d["records"][0]
        with self.assertRaises(ValueError):
            m.prepare(d,self.tax,self.saved,[])
    def test_missing_survey_definitions_fails(self):
        d=json.loads(json.dumps(self.tax))
        d["assessments"][2]["ingredients"].pop()
        with self.assertRaises(ValueError):
            m.validate(self.source,d,self.saved)
    def test_reviewed_facts_require_matching_product_identity(self):
        item=self.source["records"][0];nct=item["nctId"]
        reviewed={"schemaVersion":1,"sourceAsOf":self.source["snapshotDate"],
            "records":[{"nctId":nct,"ticker":item["ticker"],"drug":"Other",
                "indication":"Other","facts":{"eligibleUsPatients":{
                    "value":100,"status":"VERIFIED","sourceUrl":"https://example.org/fact",
                    "sourceDate":"2026-10-01","method":"survey","confidence":"HIGH"}},
                "advantages":[]}]}
        tabs,counts=m.prepare(self.source,self.tax,reviewed,[])
        self.assertEqual(counts["sourcedIngredientObservations"],0)

if __name__=="__main__":unittest.main()
