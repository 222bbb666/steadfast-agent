"""Fail if the runtime package could see benchmark answers or benchmark-specific knowledge.

The runtime (src/steadfast) must work from what any environment hands it at run
time: tools, policy text, conversation. So it must not contain:
  - references to tau2 answer fields (evaluation_criteria, nl_assertions, ...)
  - imports of tau2 (only the adapter in integrations/ may import it)
  - benchmark domain words, in English or Chinese
  - any long task ID from the frozen split

Usage:  python scripts/check_leakage.py [path ...]   (default: src/steadfast)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT_FILE = ROOT / "data" / "splits" / "tau2-split-v1.json"

ANSWER_FIELDS = [
    "evaluation_criteria",
    "nl_assertions",
    "expected_outputs",
    "reward_basis",
    "communicate_info",
    "golden",
]
IMPORT_PATTERN = re.compile(r"^\s*(from|import)\s+tau2\b", re.MULTILINE)
DOMAIN_WORDS_EN = [
    "airline", "retail", "telecom", "reservation", "flight", "baggage",
    "cabin", "refund", "exchange_delivered", "data_usage", "roaming", "sim_card",
]
DOMAIN_WORDS_ZH = ["航班", "机票", "行李", "订单", "退款", "换货", "套餐", "话费", "流量", "漫游"]
MIN_TASK_ID_LEN = 8


def forbidden_terms() -> list[str]:
    terms = ANSWER_FIELDS + DOMAIN_WORDS_EN + DOMAIN_WORDS_ZH
    split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))
    for domain in split["domains"].values():
        for part in ("dev", "distill", "test"):
            terms += [t for t in domain[part] if len(t) >= MIN_TASK_ID_LEN]
    return terms


def scan(paths: list[Path]) -> list[str]:
    terms = forbidden_terms()
    problems = []
    for base in paths:
        files = [base] if base.is_file() else sorted(base.rglob("*"))
        for f in files:
            if not f.is_file() or f.suffix in {".pyc"}:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            rel = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
            if IMPORT_PATTERN.search(text):
                problems.append(f"{rel}: imports tau2 (only integrations/ may)")
            for term in terms:
                if term.lower() in lower:
                    shown = term if len(term) <= 40 else term[:40] + "..."
                    problems.append(f"{rel}: contains forbidden term {shown!r}")
    return problems


def main() -> int:
    paths = [Path(p).resolve() for p in sys.argv[1:]] or [ROOT / "src" / "steadfast"]
    problems = scan(paths)
    for p in problems:
        print("LEAK:", p)
    if problems:
        return 1
    print(f"OK: no benchmark leakage in {', '.join(str(p.relative_to(ROOT)) for p in paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
