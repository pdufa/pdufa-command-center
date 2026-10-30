from research.predictions_page import page_configuration


def test_page_requires_explicit_data_connections(monkeypatch):
    monkeypatch.delenv("PREDICTIONS_TRIAL_SNAPSHOT", raising=False)
    monkeypatch.delenv("PREDICTIONS_JOB_DIRECTORY", raising=False)
    assert page_configuration() == (None, None)


def test_page_reads_explicit_paths(monkeypatch):
    monkeypatch.setenv("PREDICTIONS_TRIAL_SNAPSHOT", "/tmp/real-trials.json")
    monkeypatch.setenv("PREDICTIONS_JOB_DIRECTORY", "/tmp/prediction-jobs")
    assert page_configuration() == ("/tmp/real-trials.json", "/tmp/prediction-jobs")
