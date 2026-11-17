"""Source archive cross-checks use synthetic fixtures, never live network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "scripts/medical/pool_source_coverage_manifest.py"
spec = importlib.util.spec_from_file_location("pool_source_coverage_manifest", PATH)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
NCT = "NCT00000001"
SHA = "a" * 64


def fixtures(tmp_path, *, captured=True, pub_status="QUERY_SUCCEEDED_UNREVIEWED"):
    folder = tmp_path / "registry"
    cache = folder / "registry-cache"
    cache.mkdir(parents=True)
    document = {"protocolSection": {"identificationModule": {"nctId": NCT}}}
    digest = hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode()).hexdigest()
    if captured:
        (cache / (NCT + ".json")).write_text(json.dumps(document))
    state = {"sources": {NCT: {"versions": [{
        "fingerprint": digest, "cachePath": "registry-cache/" + NCT + ".json"}] if captured else []}}}
    inventory = {
        "sourceFiles": [{"path": "new-platform/frontend/data/tools-pool-snapshot.json",
                         "sha256": SHA}],
        "counts": {"poolUniqueNcts": 1},
        "records": [{"nctId": NCT, "membership": {"pool": True},
                     "rawRegistryCaptured": captured}],
    }
    leads = [{"pmid": "1234", "url": "https://pubmed.ncbi.nlm.nih.gov/1234/",
              "status": "UNREVIEWED_LEAD", "exactTrialLinkVerified": False,
              "clinicalFinding": None}] if pub_status == "QUERY_SUCCEEDED_UNREVIEWED" else []
    pubmed = {
        "schemaVersion": "pool-pubmed-unreviewed-leads-v1",
        "scope": "ALL_EXACT_POOL_TRIAL_NCTS_ALL_PHASES_ALL_STATUSES",
        "rosterSha256": SHA,
        "nctOrder": [NCT], "totalPoolTrials": 1,
        "rows": [{"nct": NCT, "status": pub_status, "publicationLeads": leads}],
    }
    (folder / "inventory.json").write_text(json.dumps(inventory))
    (folder / "ingestion-state.json").write_text(json.dumps(state))
    path = tmp_path / "pubmed.json"
    path.write_text(json.dumps(pubmed))
    return folder, path


def test_exact_pool_match_is_source_only(tmp_path):
    folder, file = fixtures(tmp_path)
    result = tool.build(folder, file)
    assert result["status"] == "SOURCE_CAPTURE_PRESENT_NOT_SCIENTIFICALLY_REVIEWED"
    assert result["rawRegistryPacketsVerifiedLocally"] == 1
    assert result["pubmedLeadsUnreviewed"] == 1
    assert result["scientificReviewsCompleted"] == 0
    assert result["fdaPredictionsComputed"] == 0
    assert result["rows"][0]["scientificScore"] is None


def test_missing_sources_are_partial_and_never_negative_findings(tmp_path):
    folder, file = fixtures(tmp_path, captured=False, pub_status="RETRY_REQUIRED")
    result = tool.build(folder, file)
    assert result["status"] == "PARTIAL_SOURCE_CAPTURE_REQUIRES_FOLLOWUP"
    assert result["pubmedQueriesFailed"] == 1
    assert result["clinicalFindingsVerified"] is False


def test_snapshot_mismatch_and_wrong_pubmed_trial_rejected(tmp_path):
    folder, file = fixtures(tmp_path)
    pubmed = json.loads(file.read_text())
    pubmed["rosterSha256"] = "b" * 64
    file.write_text(json.dumps(pubmed))
    with pytest.raises(ValueError, match="SHA mismatch"):
        tool.build(folder, file)
    pubmed["rosterSha256"] = SHA
    pubmed["rows"][0]["nct"] = "NCT00000002"
    file.write_text(json.dumps(pubmed))
    with pytest.raises(ValueError, match="research row"):
        tool.build(folder, file)


def test_tampered_registry_cache_and_wrong_trial_rejected(tmp_path):
    folder, file = fixtures(tmp_path)
    cache = folder / "registry-cache" / (NCT + ".json")
    cache.write_text(json.dumps({"protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}}))
    with pytest.raises(ValueError, match="Wrong exact-NCT"):
        tool.build(folder, file)
    folder, file = fixtures(tmp_path / "new-digest-fixture")
    statefile = folder / "ingestion-state.json"
    state = json.loads(statefile.read_text())
    state["sources"][NCT]["versions"][0]["fingerprint"] = "c" * 64
    statefile.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        tool.build(folder, file)


def test_forbidden_pubmed_lead_promotion_and_traversal_rejected(tmp_path):
    folder, file = fixtures(tmp_path)
    value = json.loads(file.read_text())
    value["rows"][0]["publicationLeads"][0]["clinicalFinding"] = "Successful"
    file.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="trust boundary"):
        tool.build(folder, file)
    folder, file = fixtures(tmp_path / "new-path-fixture")
    statefile = folder / "ingestion-state.json"
    state = json.loads(statefile.read_text())
    state["sources"][NCT]["versions"][0]["cachePath"] = "../../other-file.json"
    statefile.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="Unsafe"):
        tool.build(folder, file)
