"""Client and API must classify the same imported evidence identically."""
from datetime import date
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import Session

from app import main
from app.reconciliation_review import (ReviewPackage, valid_review_date,
                                       valid_review_source, validate_review_package)

FIXTURE = json.loads((Path(__file__).parents[2] / "validation" / "review-evidence-cases.json").read_text())


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["name"])
def test_common_evidence_contract(case):
    assert valid_review_source(case["source"]) is case["sourceValid"]
    assert valid_review_date(case["reviewedOn"], today=date.fromisoformat(FIXTURE["today"])) is case["dateValid"]


def test_bad_row_is_reported_individually_and_validation_executes_only_selects(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "evidence.sqlite3"))
    main.Base.metadata.create_all(engine)
    with Session(engine) as session:
        from datetime import datetime, timezone
        session.add(main.ProgramIdentity(source_key="TRIAL|NCT00000001", ticker="TEST", drug="drug", created_at=datetime.now(timezone.utc)))
        session.commit()
    statements = []
    event.listen(engine, "before_cursor_execute", lambda conn, cursor, statement, *rest: statements.append(statement))
    payload = ReviewPackage(schemaVersion=1, kind="pdufa-reconciliation-review-export", records=[
        {"programKey":"group", "status":"confirmed", "evidenceUrl":url,
         "reviewedOn":"2020-01-01", "exactSourceKey":"TRIAL|NCT00000001"}
        for url in ("https://[invalid-ipv6", "https://clinicaltrials.gov/study/NCT00000001")
    ])
    try:
        result = validate_review_package(payload, engine, main.ProgramIdentity)
        assert result["invalid"] == 1 and result["exactMatches"] == 1
        assert result["records"][0]["outcome"] == "INVALID_EVIDENCE"
        assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
        with Session(engine) as session:
            assert session.scalar(select(func.count(main.ProgramIdentity.id))) == 1
    finally:
        engine.dispose()
