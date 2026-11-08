"""Verify the preserved pilot originals without network or database access."""
from pathlib import Path
from xml.etree import ElementTree as ET
import gzip
import hashlib
import json

root = Path(__file__).resolve().parent
manifest = json.loads((root / "receipts.json").read_text())
assert manifest["nct"] == "NCT06081894"
for source in manifest["receipts"]:
    body = (root / source["artifact"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == source["artifactSha256"], source["sourceId"]
    assert len(body) == source["artifactBytes"]
    if source.get("compression") == "gzip":
        original = gzip.decompress(body)
        assert hashlib.sha256(original).hexdigest() == source["originalResponseSha256"]
        assert len(original) == source["originalResponseBytes"]
        feed = json.loads(original)["GetPressReleaseListResult"]
        assert len(feed) == source["responseRecordCount"]
        extracted = json.loads((root / "cytokinetics-ACACIA-20260828-extracted-release.json").read_text())
        assert extracted == next(r for r in feed if r["PressReleaseId"] == 2347)
for artifact in manifest["derivedArtifacts"]:
    assert hashlib.sha256((root / artifact["artifact"]).read_bytes()).hexdigest() == artifact["sha256"]
for failure in manifest["retrievalFailures"]:
    if failure.get("artifact"):
        assert hashlib.sha256((root / failure["artifact"]).read_bytes()).hexdigest() == failure["sha256"]
registry = json.loads((root / "NCT06081894-clinicaltrials-gov.json").read_text())
assert registry["protocolSection"]["identificationModule"]["nctId"] == manifest["nct"]
assert registry["protocolSection"]["designModule"]["phases"] == ["PHASE3"]
assert registry["hasResults"] is False and not registry.get("resultsSection")
articles = ET.parse(root / "ACACIA-HCM-pubmed.xml").findall(".//PubmedArticle")
assert {a.findtext(".//PMID") for a in articles} == {"42663312", "42667274", "42663111"}
assert all(manifest["nct"] in ET.tostring(a, encoding="unicode") for a in articles)
paper = ET.parse(root / "PMC13674599-fulltext.xml")
assert manifest["nct"] in ET.tostring(paper.getroot(), encoding="unicode")
assert any(n.text == "10.1161/CIRCULATIONAHA.126.082343"
           for n in paper.findall('.//infon[@key="article-id_doi"]'))
assert manifest["independentlyGradedScientificMethods"] == 0
assert manifest["clinicalSignoff"] is False
assert set(manifest["fdaPredictions"].values()) == {"ABSTAIN"}
assert manifest["certainty"] == "NOT_VALIDATED"
print("PASS: 4 original responses, exact NCT/DOI/PMIDs, source hashes, sponsor extraction; 0 grades/signoffs")
