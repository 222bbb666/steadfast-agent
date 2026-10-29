import json

import pytest

from evals import run_log, splits


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setenv(splits.FINAL_ENV, "1")
    return tmp_path / "final_runs.jsonl"


def test_refuses_without_final_flag(tmp_path, monkeypatch):
    monkeypatch.delenv(splits.FINAL_ENV, raising=False)
    with pytest.raises(PermissionError):
        run_log.append({"config": "F"}, git_commit="abc", log_path=tmp_path / "x.jsonl")


def test_chain_verifies(log):
    run_log.append({"config": "B1"}, git_commit="aaa", log_path=log)
    run_log.append({"config": "F"}, git_commit="bbb", log_path=log)
    ok, message = run_log.verify(log)
    assert ok, message
    assert [r["seq"] for r in run_log.read(log)] == [0, 1]


def test_detects_edited_record(log):
    run_log.append({"config": "B1"}, git_commit="aaa", log_path=log)
    run_log.append({"config": "F"}, git_commit="bbb", log_path=log)
    records = run_log.read(log)
    records[0]["config"] = "F-quietly-rerun"
    log.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    ok, message = run_log.verify(log)
    assert not ok and "record 0" in message


def test_detects_deleted_record(log):
    for config in ("B0", "B1", "F"):
        run_log.append({"config": config}, git_commit="aaa", log_path=log)
    lines = log.read_text(encoding="utf-8").splitlines()
    log.write_text(lines[0] + "\n" + lines[2] + "\n", encoding="utf-8")
    ok, _ = run_log.verify(log)
    assert not ok


def test_records_split_hash(log):
    record = run_log.append({"config": "F"}, git_commit="aaa", log_path=log)
    assert record["split_version"] == "tau2-split-v1"
    assert len(record["split_sha256"]) == 64
