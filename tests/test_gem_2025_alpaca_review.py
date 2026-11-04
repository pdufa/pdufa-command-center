"""Tests for Alpaca staging ingestion; never make network calls."""
import io
import json
import unittest

from scripts.fetch_gem_2025_alpaca_review import request_bars


class Response(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self,*_):
        self.close()


def bar(day,close):
    return {"t":day+"T05:00:00Z","o":close-.1,
            "h":close+.2,"l":close-.2,"c":close,"v":100000}


class AlpacaStageTests(unittest.TestCase):
    def test_pages_only_stage_review_not_automatic_verified(self):
        urls=[]
        def fake_fetch(request,timeout):
            self.assertEqual(timeout,30)
            self.assertEqual(request.get_header("Apca-api-key-id"),"testkey")
            url=request.full_url
            urls.append(url)
            obj=({"bars":[bar("2025-04-01",10)],
                  "next_page_token":"next"}
                 if "page_token=" not in url else
                 {"bars":[bar("2025-04-02",11)],
                  "next_page_token":None})
            return Response(json.dumps(obj).encode())
        result=request_bars("TEST","2025-01-01","2026-01-01",
                            "2025-12-31","testkey","testsecret",
                            fetch=fake_fetch)
        self.assertEqual(len(result),2)
        self.assertTrue(all(x["adjustment_status"]==
                            "PENDING_TICKER_AND_SPLIT_AUDIT" for x in result))
        self.assertEqual([x["session"] for x in result],
                         ["2025-04-01","2025-04-02"])
        self.assertTrue(all("adjustment=split" in x for x in urls))
        self.assertTrue(all("feed=sip" in x for x in urls))
        self.assertTrue(all("testsecret" not in x for x in urls))
        self.assertEqual(len(urls),2)

    def test_duplicate_session_rejected(self):
        def fake(request,timeout):
            return Response(json.dumps({
                "bars":[bar("2025-04-01",10),bar("2025-04-01",11)]
            }).encode())
        with self.assertRaisesRegex(ValueError,"Duplicate session"):
            request_bars("TEST","2025-01-01","2026-01-01",
                         "2025-12-31","a","b",fetch=fake)

    def test_invalid_symbol_does_not_call_network(self):
        def no_call(*args,**kwargs):
            self.fail("Network call not allowed")
        with self.assertRaisesRegex(ValueError,"Invalid ticker"):
            request_bars("BAD/NAME","2025-01-01","2026-01-01",
                         "2025-12-31","a","b",fetch=no_call)

    def test_outside_window_rejected(self):
        def fake(request,timeout):
            return Response(json.dumps({"bars":[bar("2027-04-01",10)]}).encode())
        with self.assertRaisesRegex(ValueError,"Out-of-window"):
            request_bars("TEST","2025-01-01","2026-01-01",
                         "2025-12-31","a","b",fetch=fake)


if __name__=="__main__":
    unittest.main()
