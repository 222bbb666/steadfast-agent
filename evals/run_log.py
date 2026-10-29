"""Append-only, hash-chained log of final runs on the sealed test split.

Each record stores the hash of the previous record, so editing or deleting
any earlier entry breaks `verify`. Together with git history this shows how
many times the test split was used and at which commit.

  python -m evals.run_log verify
  python -m evals.run_log append --config F --note "final run"   (needs STEADFAST_FINAL=1)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from evals.splits import DEFAULT_VERSION, FINAL_ENV, SPLITS_DIR

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "results" / "final_runs.jsonl"
GENESIS = "0" * 64


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read(log_path: Path = DEFAULT_LOG) -> list[dict]:
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def verify(log_path: Path = DEFAULT_LOG) -> tuple[bool, str]:
    prev = GENESIS
    for i, record in enumerate(read(log_path)):
        if record.get("seq") != i:
            return False, f"record {i}: seq is {record.get('seq')}"
        if record.get("prev_hash") != prev:
            return False, f"record {i}: prev_hash does not match record {i - 1}"
        if record.get("hash") != _digest(record):
            return False, f"record {i}: content was changed after it was written"
        prev = record["hash"]
    return True, f"{len(read(log_path))} final run(s), chain intact"


def append(
    entry: dict,
    git_commit: str,
    log_path: Path = DEFAULT_LOG,
    split_version: str = DEFAULT_VERSION,
) -> dict:
    if os.environ.get(FINAL_ENV) != "1":
        raise PermissionError(f"refusing to log a final run without {FINAL_ENV}=1")
    ok, message = verify(log_path)
    if not ok:
        raise ValueError(f"existing log is broken: {message}")

    records = read(log_path)
    split_bytes = (SPLITS_DIR / f"{split_version}.json").read_bytes()
    record = {
        "seq": len(records),
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit,
        "split_version": split_version,
        "split_sha256": hashlib.sha256(split_bytes).hexdigest(),
        **entry,
        "prev_hash": records[-1]["hash"] if records else GENESIS,
    }
    record["hash"] = _digest(record)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _clean_head() -> str:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()

    if git("status", "--porcelain"):
        raise RuntimeError("working tree is dirty; commit first so the run is reproducible")
    return git("rev-parse", "HEAD")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    add = sub.add_parser("append")
    add.add_argument("--config", required=True)
    add.add_argument("--note", default="")
    args = parser.parse_args()

    if args.command == "verify":
        ok, message = verify()
        print(("OK: " if ok else "FAIL: ") + message)
        return 0 if ok else 1

    record = append({"config": args.config, "note": args.note}, git_commit=_clean_head())
    print(f"logged final run #{record['seq']} at {record['git_commit'][:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
