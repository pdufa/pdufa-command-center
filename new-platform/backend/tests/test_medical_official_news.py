"""Official-source news watch must never manufacture FDA decisions or overwrite revisions."""
import pytest
from app.medical_official_news import official_link, parse_fda_feed, unique_cycle_match, exact_drug_alias

SAMPLE = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>FDA announces findings on aficamten</title>
<link>https://www.fda.gov/news-events/test-article</link>
<pubDate>Mon, 09 Nov 2026 18:00:00 GMT</pubDate></item>
<item><title>Untrusted item</title><link>https://attacker.example/news</link>
<pubDate>Mon, 09 Nov 2026 18:00:00 GMT</pubDate></item>
</channel></rss>"""

def test_only_official_fda_host_is_admitted():
    assert official_link("https://www.fda.gov/news-events/test")
    for link in ("https://fda.gov.attacker.example/news",
                 "http://www.fda.gov/news",
                 "https://www.fda.gov@attacker.example/news",
                 "https://www.fda.gov:999/news"):
        assert not official_link(link)

def test_feed_parsing_rejects_external_and_malformed_records():
    entries = parse_fda_feed(SAMPLE)
    assert len(entries) == 1
    assert entries[0]["url"].startswith("https://www.fda.gov/")
    with pytest.raises(ValueError):
        parse_fda_feed(b"<html>not an official RSS feed</html>")

def test_exact_cycle_identity_is_unique_not_ticker_or_related_drug_guess():
    roster = {"records":[
        {"nct":"NCT05767346","candidateApplications":[
            {"cycleId":"cytk-aficamten","ticker":"CYTK","drug":"Aficamten"}]},
        {"nct":"NCT00000002","candidateApplications":[
            {"cycleId":"cytk-aficamten","ticker":"CYTK","drug":"Aficamten"}]},
        {"nct":"NCT00000003","candidateApplications":[
            {"cycleId":"other","ticker":"OTHER","drug":"Otherdrug"}]},
    ]}
    match = unique_cycle_match("FDA announces findings on aficamten",roster)
    assert match["cycleId"] == "cytk-aficamten"
    assert match["ncts"] == ["NCT00000002","NCT05767346"]
    assert unique_cycle_match("FDA issues a policy statement",roster) is None
    roster["records"].append({"nct":"NCT00000004","candidateApplications":[
        {"cycleId":"second-aficamten","ticker":"OTHER","drug":"Aficamten"}]})
    assert unique_cycle_match("Aficamten update",roster) is None

def test_short_ambiguous_drug_alias_does_not_pass():
    assert exact_drug_alias("AD109 (combination)") is None
    assert exact_drug_alias("Aficamten") == "aficamten"
