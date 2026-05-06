from pathlib import Path
import subprocess
import sys


def test_app_imports_without_manual_src_path_injection():
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-c", "import app; print('ok')"]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_worklog_mentions_pre_release_consistency_and_ui_chinese():
    root = Path(__file__).resolve().parents[1]
    worklog = (root / "docs" / "worklog_zh.md").read_text(encoding="utf-8")

    assert "预发布" in worklog
    assert "一致性" in worklog
    assert ("中文 UI" in worklog) or ("中文界面" in worklog)


def test_user_manual_clarifies_chinese_ui_copy_with_english_contract_keys():
    root = Path(__file__).resolve().parents[1]
    manual = (root / "docs" / "user_manual_zh.md").read_text(encoding="utf-8")

    assert "中文 UI 文案" in manual
    assert "契约字段键名" in manual
    assert "保持英文" in manual
    assert "`final_text`" in manual
    assert "`decision_reason`" in manual
