import json
import random

import pytest

from evals import splits

SPLIT = splits.load_split()
UPSTREAM = splits.ROOT / "data" / "upstream" / "tau2"


@pytest.mark.parametrize("domain", ["airline", "retail", "telecom"])
def test_parts_are_disjoint_and_cover_official_split(domain):
    official = json.loads((UPSTREAM / f"{domain}_split_tasks.json").read_text(encoding="utf-8"))
    d = SPLIT["domains"][domain]
    dev, distill, test = set(d["dev"]), set(d["distill"]), set(d["test"])

    assert not dev & distill and not dev & test and not distill & test
    assert test == set(official["test"])
    assert dev | distill == set(official["train"])


def test_counts():
    assert SPLIT["counts"] == {"dev": 36, "distill": 142, "test": 100}


def test_committed_split_matches_rules():
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_split", splits.ROOT / "scripts" / "make_split.py")
    make_split = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_split)
    assert make_split.render(make_split.build()) == (
        splits.SPLITS_DIR / "tau2-split-v1.json"
    ).read_text(encoding="utf-8")


def test_dev_sampling_is_seeded_not_cherry_picked():
    official = json.loads((UPSTREAM / "retail_split_tasks.json").read_text(encoding="utf-8"))
    shuffled = official["train"][:]
    random.Random("2026:retail").shuffle(shuffled)
    assert set(SPLIT["domains"]["retail"]["dev"]) == set(shuffled[:15])


def test_test_split_is_sealed(monkeypatch):
    monkeypatch.delenv(splits.FINAL_ENV, raising=False)
    with pytest.raises(splits.SealedSplitError):
        splits.task_ids("airline", "test")
    assert len(splits.task_ids("airline", "dev")) == 6


def test_test_split_opens_only_with_final_flag(monkeypatch):
    monkeypatch.setenv(splits.FINAL_ENV, "1")
    assert len(splits.task_ids("airline", "test")) == 20
