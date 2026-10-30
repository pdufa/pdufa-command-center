"""Offline tests for authenticated SSE smoke checker (no credentials or network)."""
import io
import json
from unittest.mock import patch
from scripts import smoke_prediction_sse as smoke

NCT = "NCT01234567"
ENV = {"PDUFA_API_BASE_URL": "https://staging.example.test", "PDUFA_INTERNAL_API_KEY": "dummy-secret", "PDUFA_TEST_NCT": NCT}


class Response:
    status = 200
    headers = {"Content-Type": "text/event-stream"}

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        return self.body.encode()


def stream(nct=NCT, decision="ABSTAIN"):
    events = [{"type": "started", "nct_id": nct, "mode": "SAVED_EVIDENCE_REPLAY", "research_running": False}]
    events += [{"type": "assessment", "nct_id": nct, "assessment_id": f"S{i:02d}", "status": "NOT_ASSESSED"} for i in range(1, 41)]
    events += [{"type": "progress", "nct_id": nct} for _ in range(21)]
    events += [{"type": "complete", "nct_id": nct, "decision": decision}]
    return "".join(f'event: {e["type"]}\ndata: {json.dumps(e)}\n\n' for e in events)


def test_smoke_accepts_valid_stream(capsys):
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(stream())):
        assert smoke.main() == 0
    assert "PASS:" in capsys.readouterr().out


def test_smoke_rejects_wrong_trial(capsys):
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(stream(nct="NCT87654321"))):
        assert smoke.main() == 1
    assert "dummy-secret" not in str(capsys.readouterr())


def test_smoke_rejects_unauthorized_decision():
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(stream(decision="PASS"))):
        assert smoke.main() == 1


def test_smoke_requires_configuration(capsys):
    with patch.dict("os.environ", {}, clear=True):
        assert smoke.main() == 2
    assert "PDUFA_INTERNAL_API_KEY" in capsys.readouterr().err


def test_smoke_rejects_malformed_json_without_traceback(capsys):
    bad_frame = "event: started\\ndata: {not-json}\\n\\n".replace("\\n", "\n")
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(bad_frame)):
        assert smoke.main() == 1
    captured = capsys.readouterr()
    assert "Malformed SSE JSON" in captured.err
    assert "dummy-secret" not in captured.err


def test_smoke_rejects_invalid_utf8_without_traceback(capsys):
    class InvalidUtf8Response(Response):
        def read(self, _):
            return bytes([0xFF, 0xFE])
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=InvalidUtf8Response("")):
        assert smoke.main() == 1
    captured = capsys.readouterr()
    assert "Smoke test failed: UnicodeDecodeError" in captured.err
    assert "dummy-secret" not in captured.err


def test_smoke_rejects_non_object_json_without_traceback(capsys):
    frame = "event: started\ndata: []\n\n"
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(frame)):
        assert smoke.main() == 1
    captured = capsys.readouterr()
    assert "Event type or NCT identity mismatch" in captured.err
    assert "dummy-secret" not in captured.err


def test_smoke_rejects_duplicate_assessment_ids(capsys):
    body = stream().replace('"assessment_id": "S02"', '"assessment_id": "S01"')
    with patch.dict("os.environ", ENV), patch.object(smoke.urllib.request, "urlopen", return_value=Response(body)):
        assert smoke.main() == 1
    assert "SSE invariant failure" in capsys.readouterr().err
