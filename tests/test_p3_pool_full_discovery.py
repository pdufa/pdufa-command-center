"""Full canonical POOL exact-NCT scan regression tests."""
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("full_pool_scan",ROOT/"scripts/p3_pool_full_discovery.py")
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
NOW=datetime(2026,11,7,8,tzinfo=timezone.utc)
URL="https://api.nasdaq.com/api/quote/COGT/summary?assetclass=stocks"
class Response:
    def __init__(self,items):self.items=items
    def raise_for_status(self):pass
    def json(self):return {"studies":self.items}

def study(nct,phase="PHASE3",posted=True):
    return {"protocolSection":{"identificationModule":{"nctId":nct},
          "designModule":{"phases":[phase]},
          "statusModule":{"overallStatus":"COMPLETED",
             "resultsFirstPostDateStruct":{"date":"2026-10-01"} if posted else {}}},
          "hasResults":posted}

def fixtures():
    pool=[["ticker","company","nct_id"],["COGT","Cogent","NCT00000001"],
          ["COGT","Cogent","NCT00000002"],["COGT","Cogent","NCT00000003"],
          ["BIG","Huge Pharma","NCT00000004"]]
    p3=[["Ticker","NCT ID","Company"],["COGT","NCT00000001","Cogent"]]
    caps=[{"ticker":ticker,"market_cap":str(amount),"market_cap_source":URL,
           "market_cap_checked_at":NOW.isoformat(),"market_cap_status":"VERIFIED"}
          for ticker,amount in [("COGT",300000000),("BIG",10000000001)]]
    leads=[{"ticker":"COGT","nct_id":"NCT00000003",
            "source_url":"https://issuer.example.com/data","readout_date":"2026-10-02"}]
    def getter(url,params,timeout,headers):
        return Response([study(n,posted=n!="NCT00000003") for n in params["filter.ids"].split(",")])
    return pool,p3,caps,leads,{"cases":{}},getter

class FullPoolTests(unittest.TestCase):
    def test_pool_unique_and_nonempty(self):
        p,*_=fixtures()
        self.assertEqual(len(mod.validate_pool(p)),4)
        with self.assertRaises(ValueError):mod.validate_pool(p+[p[1]])
        with self.assertRaises(ValueError):mod.validate_pool([["bad","bad","bad"]])
    def test_cap_partition(self):
        p,_,caps,*_=fixtures()
        e,c=mod.cap_eligible(mod.validate_pool(p),caps,NOW.date())
        self.assertEqual(len(e),3)
        self.assertEqual(c["CAP_OUT_OF_BAND"],1)
        caps[0]["market_cap_checked_at"]="2026-10-01T00:00:00+00:00"
        e,c=mod.cap_eligible(mod.validate_pool(p),caps,NOW.date())
        self.assertFalse(e)
        self.assertEqual(c["CAP_UNVERIFIED_OR_STALE"],3)
    def test_strict_secondary_cap_includes_missing_but_cannot_hide_verified_outside_band(self):
        pool,p3,caps,_,_,_=fixtures()
        caps[0]["market_cap_checked_at"]="2026-10-01T00:00:00+00:00"
        secondary={"COGT":(830000000,NOW.date().isoformat(),
                    "https://stockanalysis.com/stocks/cogt/market-cap/"),
                   "BIG":(740000000,NOW.date().isoformat(),
                    "https://stockanalysis.com/stocks/big/market-cap/")}
        eligible,counters=mod.cap_eligible(mod.validate_pool(pool),caps,NOW.date(),secondary)
        self.assertEqual(len(eligible),3)
        self.assertEqual(counters["CAP_OUT_OF_BAND"],1)
        self.assertTrue(all(row["capSourceKind"]=="SECONDARY_DATED_ROUNDED_QUOTE"
                            for row in eligible.values()))
        secondary["COGT"]=(830000000,NOW.date().isoformat(),
                            "https://forged.example.com/invalid")
        eligible,_=mod.cap_eligible(mod.validate_pool(pool),caps,NOW.date(),secondary)
        self.assertFalse(eligible)

    def test_posted_registry_is_not_fda_approval(self):
        pool,p3,caps,leads,catalog,fn=fixtures()
        summary,detail=mod.execute(pool,p3,caps,leads,catalog,registry_get=fn,checked_at=NOW)
        counts=summary["counts"]
        self.assertEqual(counts["POOL_RECORDS"],4)
        self.assertEqual(counts["REGISTRY_QUERIED"],3)
        self.assertEqual(counts["EXISTING_P3"],1)
        self.assertEqual(counts["REVIEW_QUEUE"],2)
        self.assertEqual(counts["REGISTRY_RESULTS_POSTED"],2)
        self.assertEqual(counts["POST_PHASE3_NEEDS_REVIEWED_FDA_APPLICATION_PATH"],2)
        lead=next(x for x in detail["records"] if x["nct"]=="NCT00000003")
        self.assertFalse(lead["registryResultsPosted"])
        self.assertIsNotNone(lead["issuerReadoutLead"])
        self.assertTrue(all(x["reviewedFDAStage"] is None for x in detail["records"]))
    def test_11641_rows_without_any_fixed_25_or_762_cap(self):
        p=[["ticker","company","nct_id"]]+[["COGT","Cogent",f"NCT{i:08d}"] for i in range(1,2700)]
        p += [["BIG","Huge",f"NCT{i:08d}"] for i in range(2700,11642)]
        caps=[{"ticker":t,"market_cap":str(c),"market_cap_source":URL,
               "market_cap_checked_at":NOW.isoformat(),"market_cap_status":"VERIFIED"}
              for t,c in [("COGT",9999999999),("BIG",10000000001)]]
        def get(url,params,timeout,headers):
            return Response([study(n,phase="PHASE2",posted=False) for n in params["filter.ids"].split(",")])
        summary,detail=mod.execute(p,[["Ticker","NCT ID","Company"]],caps,[],{"cases":{}},
                                   registry_get=get,checked_at=NOW)
        self.assertEqual(summary["counts"]["POOL_RECORDS"],11641)
        self.assertEqual(summary["counts"]["REGISTRY_QUERIED"],2699)
        self.assertEqual(summary["counts"]["REGISTRY_BATCHES"],45)
        self.assertEqual(detail["count"],0)
    def test_real_registry_pagination_is_followed_and_exact_nct_enforced(self):
        observed=[]
        class Paginated:
            def __init__(self,study_rows,token=None):
                self.records=study_rows
                self.token=token
            def raise_for_status(self):pass
            def json(self):
                payload={"studies":self.records}
                if self.token:payload["nextPageToken"]=self.token
                return payload
        def get(url,params,timeout,headers):
            observed.append(params.copy())
            ids=params["filter.ids"].split(",")
            if "pageToken" not in params:
                return Paginated([study(ids[0])],"page-two")
            self.assertEqual(params["pageToken"],"page-two")
            return Paginated([study(ids[1])])
        records,count=mod.fetch_registry_batches(["NCT00000001","NCT00000002"],
                                                 get=get,batch_size=2)
        self.assertEqual(count,1)
        self.assertEqual(set(records),{"NCT00000001","NCT00000002"})
        self.assertEqual(len(observed),2)
        self.assertEqual(observed[0]["pageSize"],1000)

    def test_missing_registry_is_disclosed_not_a_false_negative(self):
        pool,p3,caps,leads,catalog,fn=fixtures()
        def get(url,params,timeout,headers):
            return Response([study(n) for n in params["filter.ids"].split(",") if n!="NCT00000002"])
        summary,detail=mod.execute(pool,p3,caps,leads,catalog,registry_get=get,checked_at=NOW)
        self.assertEqual(summary["status"],"PARTIAL_REGISTRY_MATCHES")
        self.assertEqual(detail["missingRegistryNcts"],["NCT00000002"])

if __name__=="__main__":unittest.main()
