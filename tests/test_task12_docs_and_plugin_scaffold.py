from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_contains_required_setup_and_run_sections() -> None:
    content = _read_text("README.md")

    assert "python -m venv venv" in content
    assert "pip install -r requirements.txt" in content
    assert "/tasks/translate" in content
    assert "PyQt" in content
    assert "Streamlit" in content


def test_docs_package_contains_required_topic_statements() -> None:
    cost_strategy = _read_text("docs/cost_strategy.md")
    worklog = _read_text("docs/worklog_zh.md")
    user_manual = _read_text("docs/user_manual_zh.md")
    presentation_script = _read_text("docs/presentation_script_zh.md")

    assert "训练无上限分段" in cost_strategy
    assert "来源声明" in worklog
    assert "词库分类下载" in user_manual
    assert "来源声明" in presentation_script


def test_browser_extension_scaffold_targets_translate_task_endpoint() -> None:
    manifest = _read_text("extensions/browser/manifest.json")
    popup_html = _read_text("extensions/browser/popup.html")
    popup_js = _read_text("extensions/browser/popup.js")

    assert '"manifest_version": 3' in manifest
    assert "MVP" in manifest
    assert "textarea" in popup_html
    assert "/tasks/translate" in popup_js
    assert "source_declaration" in popup_js
