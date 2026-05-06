from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_contains_required_setup_and_run_sections() -> None:
    content = _read_text("README.md")

    assert "python -m venv venv" in content
    assert "pip install -r requirements.txt" in content
    assert "配置 .env" in content
    assert ".\\run.ps1 -Init" in content
    assert ".\\run.ps1" in content
    assert ".\\run.ps1 -Mode desktop" in content
    assert "备用方式" in content
    assert "/tasks/translate" in content
    assert "PyQt" in content
    assert "Streamlit" in content


def test_readme_contains_run_ps1_quick_start() -> None:
    content = _read_text("README.md")

    assert ".\\run.ps1 -Init" in content
    assert ".\\run.ps1" in content
    assert ".\\run.ps1 -Mode desktop" in content


def test_docs_package_contains_required_topic_statements() -> None:
    cost_strategy = _read_text("docs/cost_strategy.md")
    worklog = _read_text("docs/worklog_zh.md")
    user_manual = _read_text("docs/user_manual_zh.md")
    presentation_script = _read_text("docs/presentation_script_zh.md")

    assert "训练无上限分段" in cost_strategy
    assert "DeepSeek" in cost_strategy and "TEx + Gen-A" in cost_strategy
    assert "Gemini" in cost_strategy and "Etym + Gen-B" in cost_strategy
    assert "watsonx.ai" in cost_strategy and "Gen-C + Arb" in cost_strategy
    assert "GPT / 千问 / Kimi" in cost_strategy
    assert "自动回退到 Mock" in cost_strategy
    assert "来源声明" in worklog
    assert "词库分类下载" in user_manual
    assert "来源声明" in presentation_script


def test_pyqt_phase1_docs_cover_interactive_workflow_and_offline_notice() -> None:
    worklog = _read_text("docs/worklog_zh.md")
    user_manual = _read_text("docs/user_manual_zh.md")

    assert "PyQt 交互式面板" in worklog
    assert "修订/确认" in worklog
    assert "复制按钮解锁" in worklog
    assert "未上传参考文本时，可回退读取" in worklog
    assert "离线提醒为非阻塞" in worklog

    assert "交互面板" in user_manual
    assert "翻译与训练分离" in user_manual
    assert "修订" in user_manual and "确认" in user_manual
    assert "仅在确认后解锁复制" in user_manual
    assert "未上传参考文本时" in user_manual and "source_declaration" in user_manual
    assert "离线提醒" in user_manual and "非阻塞" in user_manual


def test_browser_extension_scaffold_targets_translate_task_endpoint() -> None:
    manifest = _read_text("extensions/browser/manifest.json")
    popup_html = _read_text("extensions/browser/popup.html")
    popup_js = _read_text("extensions/browser/popup.js")

    assert '"manifest_version": 3' in manifest
    assert "MVP" in manifest
    assert '"activeTab"' in manifest
    assert '"storage"' in manifest
    assert "textarea" in popup_html
    assert "/tasks/translate" in popup_js
    assert "source_declaration" in popup_js


def test_popup_uses_active_tab_url_to_prefill_source_when_empty() -> None:
    popup_js = _read_text("extensions/browser/popup.js")

    assert "chrome.tabs.query" in popup_js
    assert "new URL" in popup_js
    assert "hostname" in popup_js
    assert "if (!sourceInput.value.trim())" in popup_js


def test_worklog_contains_task7_spec_review_verification_record() -> None:
    worklog = _read_text("docs/worklog_zh.md")

    assert "Task 7 规格复核验证记录" in worklog
    assert "pytest -q" in worklog and "175 passed" in worklog and "通过" in worklog
    assert "./scripts/build_exe.ps1 -Clean" in worklog and "Build complete!" in worklog and "通过" in worklog
    assert "./scripts/smoke_test_exe.ps1" in worklog and "Smoke test passed" in worklog and "通过" in worklog


def test_docs_run_ps1_examples_use_consistent_windows_style_without_malformed_prefix() -> None:
    readme = _read_text("README.md")
    worklog = _read_text("docs/worklog_zh.md")
    user_manual = _read_text("docs/user_manual_zh.md")

    docs = [readme, worklog, user_manual]
    malformed_patterns = ["\\.\\run.ps1", "\\./run.ps1"]

    for content in docs:
        for malformed in malformed_patterns:
            assert malformed not in content

    assert ".\\run.ps1 -Init" in readme
    assert ".\\run.ps1 -Init" in worklog
    assert ".\\run.ps1 -Init" in user_manual


def test_docs_cover_network_status_visibility_and_manual_refresh_mentions() -> None:
    worklog = _read_text("docs/worklog_zh.md")
    user_manual = _read_text("docs/user_manual_zh.md")

    assert "/system/network" in worklog
    assert "手动刷新" in worklog
    assert "/system/network" in user_manual
    assert "手动刷新" in user_manual


def test_user_manual_documents_mode_semantics_for_web_desktop_all() -> None:
    user_manual = _read_text("docs/user_manual_zh.md")

    assert "web`：启动 API" in user_manual
    assert "desktop`：启动 API（不启动 Streamlit）+ PyQt" in user_manual
    assert "all`：启动 API + Streamlit + PyQt" in user_manual
