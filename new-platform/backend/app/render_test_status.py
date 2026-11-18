"""Read-only isolated Render preview health endpoint; no production imports."""
from fastapi import FastAPI

app = FastAPI(title="PDUFA isolated synthetic regression preview")

@app.get("/health")
def health():
    return {"status": "build_regressions_passed", "scope": "synthetic_l1_l6_only",
            "production_writes": False, "fda_predictions": "NOT_CALIBRATED"}
