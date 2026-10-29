"""Access to the frozen tau2 split. The test part is sealed until the final run."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR = ROOT / "data" / "splits"
DEFAULT_VERSION = "tau2-split-v1"
PARTS = ("dev", "distill", "test")
FINAL_ENV = "STEADFAST_FINAL"


class SealedSplitError(PermissionError):
    pass


def load_split(version: str = DEFAULT_VERSION) -> dict:
    return json.loads((SPLITS_DIR / f"{version}.json").read_text(encoding="utf-8"))


def task_ids(domain: str, part: str, version: str = DEFAULT_VERSION) -> list[str]:
    if part not in PARTS:
        raise ValueError(f"unknown part {part!r}, expected one of {PARTS}")
    if part == "test" and os.environ.get(FINAL_ENV) != "1":
        raise SealedSplitError(
            f"The test split is sealed. Set {FINAL_ENV}=1 only for the single "
            "final run, which must be recorded with `python -m evals.run_log append`."
        )
    return list(load_split(version)["domains"][domain][part])
