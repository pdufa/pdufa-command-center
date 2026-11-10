"""R50 original FDA FY2024 approved cohort PDF rows: provenance and anti-overclaim."""
import pytest
from scripts.build_fda_fy2024_cycle_events_r50 import derive_page_events,extract

def words(cycle="First",action="CR",n=3):
    return [(351,180+i*25,361,187+i*25,cycle) for i in range(n)]+[
      (458,180+i*25,465,187+i*25,action) for i in range(n)]
def test_row_level_historical_fda_cycle_actions_never_get_independent_case_identity():
    rows=derive_page_events(words("Second","CR"),91)
    assert len(rows)==3
    assert all(r["printedFdaCycleOrdinal"]==2 for r in rows)
    assert all(r["originalFdaAppendixActionMeaning"]=="COMPLETE_RESPONSE" for r in rows)
    assert all(r["regulatorApplicationNumber"] is None for r in rows)
    assert all(r["regulatorActionDate"] is None for r in rows)
    assert all(r["exactNctIds"]==[] for r in rows)
    assert all(r["eligibleForHistoricalFDAForecastAccuracy"] is False for r in rows)

def test_mismatched_or_colliding_historical_fda_source_rows_fail_closed():
    with pytest.raises(ValueError,match="CARDINALITY"):
        derive_page_events(words()[:-1],83)
    r=words()
    r[-1]=(458,180,465,187,"CR")
    with pytest.raises(ValueError,match="AMBIGUOUS"):
        derive_page_events(r,83)
    with pytest.raises(ValueError,match="OUT_OF_APPROVED_ONLY_APPENDIX"):
        derive_page_events(words(),82)

def test_non_fda_codes_and_footer_do_not_become_actions():
    r=words(n=1)+[(458,720,466,726,"AP"),(350,720,358,726,"Fourth"),
                   (458,330,465,336,"NME"),(350,331,355,338,"New")]
    x=derive_page_events(r,87)
    assert len(x)==1 and x[0]["originalFdaAppendixActionCode"]=="CR"

def test_unknown_source_document_cannot_be_treated_as_valid_backtest():
    with pytest.raises(ValueError,match="SOURCE_SHA_MISMATCH"):
        extract(b"%PDF fake","2026-11-09T20:00:00Z")
