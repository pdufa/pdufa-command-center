"""Rate-limit-safe retry planning for an immutable original-source archive."""
from datetime import datetime, timezone
from io import BytesIO
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("registry_rate_limit_retry_test",ROOT/"scripts/collect_deep_medical_intelligence.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NCT="NCT00143455"
OTHER="NCT00000001"


def packet(nct):
    return {"protocolSection":{"identificationModule":{"nctId":nct}}}


def test_only_missing_nct_selected_and_valid_cache_preserved(tmp_path):
    client=mod.RegistryClient(report=tmp_path,retries=2)
    client.accept(OTHER,packet(OTHER),"OFFICIAL_CT_GOV_API_V2",
                  datetime.now(timezone.utc).isoformat())
    client.state["sources"][NCT]={
        "nctId":NCT,"versions":[],"lastError":"HTTPError: HTTP Error 429: Too Many Requests"}
    assert mod.uncaptured_source_ncts({OTHER,NCT},client)=={NCT}
    assert client.cached(OTHER)[0]==packet(OTHER)


def test_rate_limit_retry_after_obeyed_and_record_kept_exact(tmp_path):
    client=mod.RegistryClient(report=tmp_path,retries=2,request_delay=3)
    calls=[]
    sleeps=[]
    def opener(*args,**kwargs):
        calls.append(args)
        if len(calls)==1:
            raise HTTPError("https://clinicaltrials.gov/api/v2/studies/"+NCT,429,
                            "Too Many Requests",{"Retry-After":"15"},None)
        return BytesIO(json.dumps(packet(NCT)).encode())
    with patch.object(mod,"urlopen",side_effect=opener), patch.object(mod.time,"sleep",side_effect=sleeps.append):
        returned,value,error,origin=client.fetch(NCT, resume=True)
    assert returned==NCT and value==packet(NCT)
    assert error is None and origin=="OFFICIAL_CT_GOV_API_V2"
    assert len(calls)==2
    assert sleeps==[3,15,3]


def test_untrusted_invalid_retry_after_is_bounded(tmp_path):
    client=mod.RegistryClient(report=tmp_path,retries=2,request_delay=0)
    def opener(*args,**kwargs):
        if not hasattr(opener,"n"):
            opener.n=1
            raise HTTPError("https://clinicaltrials.gov",429,"Throttled",{"Retry-After":"not-a-time"},None)
        return BytesIO(json.dumps(packet(NCT)).encode())
    delays=[]
    with patch.object(mod,"urlopen",side_effect=opener),patch.object(mod.time,"sleep",side_effect=delays.append):
        result=client.fetch(NCT)
    assert result[2] is None and delays==[10]


def test_invalid_rate_limit_request_settings_fail_closed(tmp_path):
    for delay in (-1,61,"bad"):
        try:
            mod.RegistryClient(report=tmp_path,request_delay=delay)
        except ValueError:
            pass
        else:
            raise AssertionError("Unbounded/invalid retry delay accepted")
