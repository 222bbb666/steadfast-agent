"""Build the frozen evaluation split from the official tau2-bench splits.

Rules (fixed before any task is run, see docs/EVALUATION.md):
  test    = official `test` split, all three domains (100 tasks)
  dev     = 20% of official `train`, sampled per domain with seed 2026
  distill = the rest of official `train`; only source of fine-tuning data

Usage:
  python scripts/make_split.py           # write data/splits/tau2-split-v1.json
  python scripts/make_split.py --check   # fail if the committed file differs
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_DIR = ROOT / "data" / "upstream" / "tau2"
OUTPUT = ROOT / "data" / "splits" / "tau2-split-v1.json"

UPSTREAM_REPO = "https://github.com/sierra-research/tau2-bench"
UPSTREAM_COMMIT = "7aad81c37a3a78b4ed3e4866769f851400c64415"
DOMAINS = ("airline", "retail", "telecom")
SEED = 2026
DEV_FRACTION = 0.2


def build() -> dict:
    domains = {}
    for domain in DOMAINS:
        path = UPSTREAM_DIR / f"{domain}_split_tasks.json"
        raw = path.read_bytes()
        official = json.loads(raw)
        train, test = official["train"], official["test"]

        rng = random.Random(f"{SEED}:{domain}")
        shuffled = train[:]
        rng.shuffle(shuffled)
        dev_set = set(shuffled[: round(len(train) * DEV_FRACTION)])

        domains[domain] = {
            "upstream_file_sha256": hashlib.sha256(raw).hexdigest(),
            "dev": [t for t in train if t in dev_set],
            "distill": [t for t in train if t not in dev_set],
            "test": list(test),
        }

    counts = {
        name: sum(len(d[name]) for d in domains.values())
        for name in ("dev", "distill", "test")
    }
    return {
        "version": "tau2-split-v1",
        "upstream": {"repo": UPSTREAM_REPO, "commit": UPSTREAM_COMMIT},
        "rules": {
            "test": "official test split",
            "dev": f"{int(DEV_FRACTION * 100)}% of official train per domain, "
            f"random.Random('{SEED}:<domain>')",
            "distill": "official train minus dev",
        },
        "counts": counts,
        "domains": domains,
    }


def render(split: dict) -> str:
    return json.dumps(split, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    text = render(build())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            print(f"FAIL: {OUTPUT.relative_to(ROOT)} does not match the rules")
            return 1
        print(f"OK: {OUTPUT.relative_to(ROOT)} matches the rules")
        return 0

    if OUTPUT.exists():
        print(f"Refusing to overwrite frozen split {OUTPUT.relative_to(ROOT)}.")
        print("Create tau2-split-v2 instead and record why in docs/EVALUATION.md.")
        return 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
