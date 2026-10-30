from dataclasses import replace

from research.fda_prediction_membership_gate import check_prediction_membership
from research.fda_prospective_outcome_scoring import FrozenPrediction
from research.fda_prospective_prediction_ledger import append_prediction


def test_exact_forecast_membership(tmp_path):
    path = tmp_path / "predictions.jsonl"
    fields = dict(
        trial_id="EXAMPLE", prediction="ABSTAIN",
        cutoff_utc="2026-12-01T00:00:00Z",
        recorded_at_utc="2026-11-01T00:00:00Z",
        model_commit="abc123", evidence_manifest_sha256="a" * 64,
    )
    head = append_prediction(path, **fields)
    prediction = FrozenPrediction(
        fields["trial_id"], fields["prediction"],
        fields["recorded_at_utc"], fields["cutoff_utc"], head,
    )
    assert check_prediction_membership(
        path, expected_head_sha256=head, prediction=prediction
    ) == "LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED"
    assert check_prediction_membership(
        path, expected_head_sha256=head, prediction=replace(prediction, prediction="PASS")
    ) == "PREDICTION_FIELDS_MISMATCH"
    assert check_prediction_membership(
        path, expected_head_sha256=head, prediction=replace(prediction, ledger_entry_hash="f" * 64)
    ) == "PREDICTION_NOT_UNIQUE"
    assert check_prediction_membership(
        path, expected_head_sha256="0" * 64, prediction=prediction
    ) == "LEDGER_NOT_VERIFIED"
