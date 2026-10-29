import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_leakage", ROOT / "scripts" / "check_leakage.py")
check_leakage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_leakage)


def test_runtime_package_is_clean():
    assert check_leakage.scan([ROOT / "src" / "steadfast"]) == []


def test_catches_answer_field(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("expected = task.evaluation_criteria.actions\n", encoding="utf-8")
    assert any("evaluation_criteria" in p for p in check_leakage.scan([f]))


def test_catches_tau2_import(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("from tau2.data_model.tasks import Task\n", encoding="utf-8")
    assert any("imports tau2" in p for p in check_leakage.scan([f]))


def test_catches_chinese_domain_word(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text('RULE = "退款前必须确认订单状态"\n', encoding="utf-8")
    assert check_leakage.scan([f])


def test_catches_long_task_id(tmp_path):
    split = check_leakage.json.loads(check_leakage.SPLIT_FILE.read_text(encoding="utf-8"))
    task_id = split["domains"]["telecom"]["test"][0]
    f = tmp_path / "bad.py"
    f.write_text(f'SKIP = ["{task_id}"]\n', encoding="utf-8")
    assert check_leakage.scan([f])
