"""Conservative adapter for the existing Next.js /api/workspace response.

The workspace's marketCap is an observation in USD, not a validated cap
without a source and observation timestamp. No live endpoint is contacted.
"""
from datetime import datetime
from research.preliminary_candidate_scope import preliminary_candidate_scope


def adapt_workspace_candidates(workspace):
    if not isinstance(workspace, dict) or not isinstance(workspace.get("pipeline"), list):
        raise ValueError("workspace pipeline missing")
    health = workspace.get("sourceHealth")
    parity = health.get("pipelineSourceParity") if isinstance(health, dict) else None
    if not isinstance(parity, dict) or type(parity.get("exactPrograms")) is not int:
        raise ValueError("workspace source parity missing")
    if parity["exactPrograms"] != len(workspace["pipeline"]):
        raise ValueError("workspace source parity mismatch")
    if health.get("state") in ("STALE", "UNAVAILABLE"):
        raise ValueError("workspace source unhealthy")
    results = []
    for candidate in workspace["pipeline"]:
        if not isinstance(candidate, dict):
            raise ValueError("malformed workspace candidate")
        key = candidate.get("programId") or candidate.get("id")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("candidate has no program identifier")
        # Membership in the returned Pipeline is not proof of passing its
        # separately configured restrictions; fail closed.
        source = candidate.get("capSource")
        observed = candidate.get("capChecked")
        dated = isinstance(observed, str) and bool(observed.strip())
        row = {
            "publicly_traded": bool(candidate.get("ticker")) and
                               candidate.get("ticker") != "PRIVATE",
            "market_cap_usd": candidate.get("marketCap") if source and dated else None,
            "pipeline_member": False,
            "fda_pdufa_target_confirmed": False,
        }
        screening = preliminary_candidate_scope(row)
        results.append({"program_id": key, "ticker": candidate.get("ticker"),
                        **screening})
    return {"records": results, "total": len(results),
            "prediction_status": "ABSTAIN", "research_only": True,
            "restrictions_verified": False, "source": "workspace-pipeline"}
