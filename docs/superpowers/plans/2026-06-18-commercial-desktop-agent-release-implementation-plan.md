# Commercial Desktop Translation Agent Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a modern PySide6 Windows translation Agent, E-drive development runtimes, portable and Inno Setup releases, built-in help, safe external-tool adapters, and commercial/open-source release evidence without live remote API calls.

**Architecture:** Preserve the existing `consensus_translation` domain and controller layer, introduce one authoritative runtime layout and installed/developer diagnostics, then add a modular `desktop_qt` presentation package. Build the Qt entrypoint with PyInstaller and package it through Inno Setup; runtime payloads and user data resolve from the selected install root, while the development installation remains under `E:\Cn-Jp Translate\.runtime`.

**Tech Stack:** Python 3.13, PySide6, pytest/pytest-qt, SQLite, PyInstaller, Inno Setup 6, Tesseract 5.5, Unbabel COMET sidecar, PowerShell.

---

## Work package order

1. Delivery foundation: Tasks 1-3.
2. PySide6 desktop product: Tasks 4-6.
3. E-drive runtimes and connectors: Tasks 7-8.
4. Packaging and release: Tasks 9-12.

Each package ends in runnable software and a focused commit. Do not begin a later package while an earlier package has failing focused tests.

### Task 1: Hermetic tests and one runtime layout

**Files:**
- Create: `tests/conftest.py`
- Modify: `src/consensus_translation/agent_runtime.py`
- Modify: `src/consensus_translation/desktop_agent_app.py`
- Test: `tests/test_agent_runtime.py`
- Test: `tests/test_workflows.py`

- [x] **Step 1: Write the failing runtime layout tests**

Add tests that define the public API before implementation:

```python
from consensus_translation.agent_runtime import RuntimeLayout


def test_runtime_layout_uses_explicit_install_root(tmp_path):
    install_root = tmp_path / "installed"
    layout = RuntimeLayout.from_roots(
        install_root=install_root,
        data_root=install_root / "data",
    )

    assert layout.install_root == install_root.resolve()
    assert layout.runtime_root == (install_root / "runtime").resolve()
    assert layout.tesseract_command == (
        install_root / "runtime" / "Tesseract-OCR" / "tesseract.exe"
    ).resolve()
    assert layout.comet_command == (
        install_root / "runtime" / "comet-env" / "Scripts" / "comet-score.exe"
    ).resolve()
    assert layout.comet_model_root == (install_root / "runtime" / "comet-models").resolve()
    assert layout.data_root == (install_root / "data").resolve()


def test_runtime_layout_reads_legacy_project_runtime_settings(tmp_path):
    project_root = tmp_path / "project"
    runtime_root = project_root / ".runtime"
    runtime_root.mkdir(parents=True)
    runtime_root.joinpath("runtime-settings.json").write_text(
        json.dumps({
            "runtime_root": str(runtime_root),
            "tesseract_command": str(runtime_root / "Tesseract-OCR" / "tesseract.exe"),
            "comet_command": str(runtime_root / "comet-env" / "Scripts" / "comet-score.exe"),
            "comet_model_storage_path": str(runtime_root / "comet-models"),
        }),
        encoding="utf-8",
    )

    layout = RuntimeLayout.discover(project_root=project_root)

    assert layout.runtime_root == runtime_root.resolve()
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
$env:LOCALAPPDATA = Join-Path (Get-Location) '.pytest_localappdata\task1-red'
E:\Ana\python.exe -m pytest -q tests\test_agent_runtime.py
```

Expected: collection fails because `RuntimeLayout` is not defined.

- [x] **Step 3: Implement `RuntimeLayout` and route controller resolution through it**

Implement an immutable dataclass in `agent_runtime.py`:

```python
@dataclass(frozen=True)
class RuntimeLayout:
    install_root: Path
    runtime_root: Path
    data_root: Path
    tesseract_command: Path
    comet_command: Path
    comet_model_root: Path

    @classmethod
    def from_roots(cls, install_root: str | Path, data_root: str | Path | None = None):
        install = Path(install_root).resolve()
        runtime = install / "runtime"
        data = Path(data_root).resolve() if data_root else install / "data"
        return cls(
            install_root=install,
            runtime_root=runtime,
            data_root=data,
            tesseract_command=runtime / "Tesseract-OCR" / "tesseract.exe",
            comet_command=runtime / "comet-env" / "Scripts" / "comet-score.exe",
            comet_model_root=runtime / "comet-models",
        )

    @classmethod
    def discover(cls, project_root=None, install_root=None, data_root=None):
        if install_root is not None:
            return cls.from_roots(install_root, data_root)
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        settings = load_runtime_settings(root)
        if settings:
            runtime_value = Path(settings.get("runtime_root", root / ".runtime"))
            runtime = runtime_value if runtime_value.is_absolute() else root / runtime_value
            runtime = runtime.resolve()
            data = Path(data_root).resolve() if data_root else (root / "data").resolve()
            return cls(
                install_root=root,
                runtime_root=runtime,
                data_root=data,
                tesseract_command=Path(settings.get(
                    "tesseract_command", runtime / "Tesseract-OCR" / "tesseract.exe"
                )).resolve(),
                comet_command=Path(settings.get(
                    "comet_command", runtime / "comet-env" / "Scripts" / "comet-score.exe"
                )).resolve(),
                comet_model_root=Path(settings.get(
                    "comet_model_storage_path", runtime / "comet-models"
                )).resolve(),
            )
        packaged_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else root
        return cls.from_roots(packaged_root, data_root)
```

Replace controller calls to `_project_root()` for runtime commands with one injected `RuntimeLayout`. Preserve the old resolver functions as compatibility wrappers around the layout.

- [x] **Step 4: Add automatic pytest user-data isolation**

Create `tests/conftest.py`:

```python
import os
from pathlib import Path


def pytest_configure(config):
    if "LOCALAPPDATA" not in os.environ or "ConsensusTranslation" not in os.environ["LOCALAPPDATA"]:
        root = Path(__file__).resolve().parents[1]
        isolated = root / ".pytest_localappdata" / "automatic"
        isolated.mkdir(parents=True, exist_ok=True)
        os.environ["LOCALAPPDATA"] = str(isolated)
```

Use a session fixture instead if pytest ordering shows imports occurring before `pytest_configure`; the invariant is that `E:\Ana\python.exe -m pytest -q` never touches the real user profile.

- [x] **Step 5: Run GREEN tests**

Run:

```powershell
E:\Ana\python.exe -m pytest -q tests\test_agent_runtime.py tests\test_workflows.py tests\test_desktop_agent_app.py
```

Expected: all selected tests pass and no `C:\Users\<username>\AppData\Local\ConsensusTranslation` access occurs.

- [x] **Step 6: Commit**

```powershell
git add tests/conftest.py tests/test_agent_runtime.py src/consensus_translation/agent_runtime.py src/consensus_translation/desktop_agent_app.py
git commit -m "fix: unify runtime layout and isolate tests"
```

### Task 2: Installed versus developer diagnostics

**Files:**
- Modify: `src/consensus_translation/agent_diagnostics.py`
- Modify: `src/consensus_translation/desktop_agent_app.py`
- Test: `tests/test_agent_diagnostics.py`
- Test: `tests/test_desktop_agent_app.py`

- [x] **Step 1: Write failing installed-mode diagnostic tests**

```python
def test_installed_diagnostics_does_not_require_build_tooling(tmp_path):
    install_root = tmp_path / "installed"
    app_dir = install_root / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")

    report = run_desktop_diagnostics(
        install_root,
        mode="installed",
        command_runner=lambda command: CommandResult(0, "ok", ""),
        import_checker=lambda name: None,
    )

    checks = {item.check_id: item for item in report.checks}
    assert "desktop_packaging" not in checks
    assert checks["desktop_install"].status == "ok"
    assert report.counts["error"] == 0


def test_ocr_diagnostics_checks_required_languages(tmp_path):
    def runner(command):
        if command[-1] == "--version":
            return CommandResult(0, "tesseract 5.5", "")
        return CommandResult(0, "List of available languages (2):\neng\nosd", "")

    report = run_desktop_diagnostics(
        tmp_path,
        mode="installed",
        command_runner=runner,
        import_checker=lambda name: None,
        required_ocr_languages=("eng", "jpn"),
    )

    check = next(item for item in report.checks if item.check_id == "ocr_tesseract")
    assert check.status == "warning"
    assert "jpn" in " ".join(check.details)
```

- [x] **Step 2: Verify RED**

Run:

```powershell
E:\Ana\python.exe -m pytest -q tests\test_agent_diagnostics.py tests\test_desktop_agent_app.py
```

Expected: `run_desktop_diagnostics()` rejects `mode` and `required_ocr_languages`.

- [x] **Step 3: Implement diagnostic profiles**

Add `mode: Literal["developer", "installed"] = "developer"`, `runtime_layout`, and `required_ocr_languages`. Developer mode keeps packaging/release checks. Installed mode checks the actual executable or supplied `install_root`, writable runtime/data roots, help payload, Tesseract version/languages, COMET CLI/model, provider config contract, and manual GUI status.

Change OCR probing to execute both:

```python
[tesseract_command, "--version"]
[tesseract_command, "--list-langs"]
```

Make `desktop_agent_app --diagnostics` default to `installed` when `sys.frozen` is true, and expose `--diagnostics-mode developer|installed` for explicit control.

- [x] **Step 4: Verify packaged CLI behavior at source level**

Run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
E:\Ana\python.exe -m consensus_translation.desktop_agent_app --diagnostics --diagnostics-mode installed --install-root . --data-dir .\.pytest_tmp_runtime\installed-data --report-json .\.pytest_tmp_runtime\installed-report.json
```

Expected: no missing PyInstaller/source/dist error appears; optional runtime gaps are warnings.

- [x] **Step 5: Run GREEN tests and commit**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_agent_diagnostics.py tests\test_desktop_agent_app.py tests\test_desktop_packaging.py
git add src/consensus_translation/agent_diagnostics.py src/consensus_translation/desktop_agent_app.py tests/test_agent_diagnostics.py tests/test_desktop_agent_app.py
git commit -m "fix: separate installed and developer diagnostics"
```

### Task 3: Commercial-safe engine registry and release notices

**Files:**
- Create: `src/consensus_translation/engine_registry.py`
- Create: `tests/test_engine_registry.py`
- Create: `LICENSE`
- Create: `NOTICE`
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `MODEL_LICENSES.md`
- Create: `PRIVACY.md`
- Modify: `src/consensus_translation/engines.py`
- Modify: `src/consensus_translation/workflows.py`
- Modify: `README.md`

- [x] **Step 1: Write failing release-profile tests**

```python
from consensus_translation.engine_registry import EngineRegistry


def test_commercial_safe_profile_excludes_nllb():
    registry = EngineRegistry.default()
    ids = [entry.engine_id for entry in registry.enabled_for("commercial-safe")]
    assert "marian-opus-direct" in ids
    assert "marian-opus-pivot" in ids
    assert "nllb-200-distilled-600m" not in ids


def test_research_profile_marks_nllb_as_user_download():
    entry = EngineRegistry.default().get("nllb-200-distilled-600m")
    assert entry.license_id == "CC-BY-NC-4.0"
    assert entry.bundled is False
    assert entry.requires_license_acceptance is True
```

- [x] **Step 2: Verify RED**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_engine_registry.py
```

Expected: import failure for `engine_registry`.

- [x] **Step 3: Implement registry and commercial-safe workflow selection**

Define:

```python
@dataclass(frozen=True)
class EngineDescriptor:
    engine_id: str
    provider_kind: str
    model_ids: Sequence[str]
    license_id: str
    commercial_use: bool
    bundled: bool
    requires_license_acceptance: bool


class EngineRegistry:
    def __init__(self, entries: Sequence[EngineDescriptor]):
        self._entries = {entry.engine_id: entry for entry in entries}

    @classmethod
    def default(cls) -> "EngineRegistry":
        return cls([
            EngineDescriptor(
                "marian-opus-direct", "local", ("Helsinki-NLP/opus-mt-*",),
                "CC-BY-4.0", True, False, False,
            ),
            EngineDescriptor(
                "marian-opus-pivot", "local", ("Helsinki-NLP/opus-mt-*-en", "Helsinki-NLP/opus-mt-en-*"),
                "CC-BY-4.0", True, False, False,
            ),
            EngineDescriptor(
                "nllb-200-distilled-600m", "local", ("facebook/nllb-200-distilled-600M",),
                "CC-BY-NC-4.0", False, False, True,
            ),
        ])

    def enabled_for(self, profile: str) -> list[EngineDescriptor]:
        if profile == "commercial-safe":
            return [entry for entry in self._entries.values() if entry.commercial_use]
        if profile == "research":
            return list(self._entries.values())
        raise ValueError(f"unknown release profile: {profile}")

    def get(self, engine_id: str) -> EngineDescriptor:
        return self._entries[engine_id]
```

Keep `LocalEngineB` available only when profile `research` is explicitly selected. Implement an OPUS direct candidate and an OPUS English-pivot candidate for `commercial-safe`, de-duplicating identical outputs before MDWC.

- [x] **Step 4: Add release documents with exact current boundaries**

Use Apache-2.0 project text in `LICENSE`. `MODEL_LICENSES.md` must list each actual model ID and its license; it must state that `facebook/nllb-200-distilled-600M` is not in commercial bundles. `PRIVACY.md` must state local defaults, explicit remote data scopes, DPAPI credential storage, and no telemetry unless added and disclosed later.

- [x] **Step 5: Verify and commit**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_engine_registry.py tests\test_engines.py tests\test_workflows.py
git add src/consensus_translation/engine_registry.py src/consensus_translation/engines.py src/consensus_translation/workflows.py tests/test_engine_registry.py LICENSE NOTICE THIRD_PARTY_NOTICES.md MODEL_LICENSES.md PRIVACY.md README.md
git commit -m "feat: add commercial-safe engine profile and notices"
```

### Task 4: PySide6 application shell

**Files:**
- Create: `requirements-qt.txt`
- Create: `src/consensus_translation/desktop_qt/__init__.py`
- Create: `src/consensus_translation/desktop_qt/application.py`
- Create: `src/consensus_translation/desktop_qt/main_window.py`
- Create: `src/consensus_translation/desktop_qt/navigation.py`
- Create: `src/consensus_translation/desktop_qt/theme.py`
- Create: `tests/test_desktop_qt_shell.py`
- Create: `run_desktop_qt.ps1`

- [x] **Step 1: Add dependencies and failing offscreen shell test**

`requirements-qt.txt` contains exact compatible ranges:

```text
PySide6>=6.8,<6.10
pytest-qt>=4.4,<5
```

Test:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from consensus_translation.desktop_qt.application import create_application
from consensus_translation.desktop_qt.main_window import MainWindow


def test_main_window_exposes_release_navigation(qtbot, tmp_path):
    app = create_application([])
    window = MainWindow(controller=None, data_root=tmp_path)
    qtbot.addWidget(window)

    assert window.windowTitle() == "共识翻译 Agent"
    assert window.navigation_labels() == [
        "首页", "翻译工作台", "项目与任务", "词库与风格",
        "输入连接器", "Provider 与评估器", "诊断与运行时", "帮助中心",
    ]
```

- [x] **Step 2: Install Qt packages into the E-drive Python and verify RED**

```powershell
E:\Ana\python.exe -m pip install -r requirements-qt.txt
$env:QT_QPA_PLATFORM = 'offscreen'
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_shell.py
```

Expected: import failure for `desktop_qt` before implementation.

- [x] **Step 3: Implement the shell**

Create one `QMainWindow` with a fixed-width navigation list, `QStackedWidget`, top project/status bar, status bar, and eight page placeholders represented by real QWidget subclasses. Apply a restrained Windows-native light/dark palette through Qt stylesheets; do not introduce image assets or a new brand identity.

`create_application(argv)` must reuse an existing `QApplication` and set organization/application names for stable settings.

- [x] **Step 4: Add source launcher**

`run_desktop_qt.ps1` resolves `E:\Ana\python.exe`, sets `PYTHONPATH=src`, and runs `python -m consensus_translation.desktop_qt.application`; fallback lookup checks C before E if the configured interpreter is missing.

- [x] **Step 5: Verify and commit**

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_shell.py
git add requirements-qt.txt run_desktop_qt.ps1 src/consensus_translation/desktop_qt tests/test_desktop_qt_shell.py
git commit -m "feat: add PySide6 desktop application shell"
```

### Task 5: Functional workbench, projects, lexicon, providers, and diagnostics pages

**Files:**
- Create: `src/consensus_translation/desktop_qt/application_service.py`
- Create: `src/consensus_translation/desktop_qt/pages/home.py`
- Create: `src/consensus_translation/desktop_qt/pages/workbench.py`
- Create: `src/consensus_translation/desktop_qt/pages/projects.py`
- Create: `src/consensus_translation/desktop_qt/pages/lexicon.py`
- Create: `src/consensus_translation/desktop_qt/pages/providers.py`
- Create: `src/consensus_translation/desktop_qt/pages/diagnostics.py`
- Modify: `src/consensus_translation/desktop_qt/main_window.py`
- Test: `tests/test_desktop_qt_workflows.py`

- [x] **Step 1: Write failing UI workflow tests with a real controller boundary**

```python
def test_workbench_translates_and_renders_result(qtbot, qt_controller):
    window = MainWindow(controller=qt_controller)
    qtbot.addWidget(window)
    window.show_page("翻译工作台")
    page = window.current_page()
    page.source_editor.setPlainText("alpha beta")

    qtbot.mouseClick(page.translate_button, Qt.LeftButton)

    assert page.result_editor.toPlainText()
    assert page.status_label.text() in {"已完成", "等待人工确认"}


def test_provider_save_never_displays_secret(qtbot, qt_controller):
    window = MainWindow(controller=qt_controller)
    page = window.page("Provider 与评估器")
    page.api_key_input.setText("sk-test-secret")
    qtbot.mouseClick(page.save_button, Qt.LeftButton)

    assert "sk-test-secret" not in window.visible_text()
    assert page.api_key_input.text() == ""
```

- [x] **Step 2: Verify RED**

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_workflows.py
```

Expected: missing pages/service APIs.

- [x] **Step 3: Implement an application service, not direct database UI access**

`DesktopApplicationService` wraps `DesktopAgentController` and exposes typed methods for translate, preview/confirm remote calls, profiles, recent files, runs, pending lexicon events, provider save/load/smoke, diagnostics, local acceptance, and artifact export. UI pages emit Qt signals and call only this service.

- [x] **Step 4: Implement functional pages**

The workbench supports text/file input, languages, topic, mode, training/validation files, evaluator, candidate/result panes, preflight confirmation, run confirmation, and artifact export. Project/task, lexicon, provider, and diagnostic pages load real controller data and show empty/error states with recovery actions.

Remote smoke uses a static/mock provider fixture when no real credential is configured; no test or default button initiates a live remote call.

- [x] **Step 5: Verify and commit**

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_shell.py tests\test_desktop_qt_workflows.py tests\test_desktop_agent_app.py
git add src/consensus_translation/desktop_qt tests/test_desktop_qt_workflows.py
git commit -m "feat: connect PySide6 pages to agent workflows"
```

### Task 6: Searchable help and external-tool connectors

**Files:**
- Create: `src/consensus_translation/help_content.py`
- Create: `src/consensus_translation/desktop_qt/pages/help.py`
- Create: `src/consensus_translation/desktop_qt/pages/connectors.py`
- Create: `docs/help/quick-start.md`
- Create: `docs/help/connectors.md`
- Create: `docs/help/providers.md`
- Create: `docs/help/runtime-troubleshooting.md`
- Create: `docs/help/privacy-and-licenses.md`
- Modify: `src/consensus_translation/agent_input_plugins.py`
- Test: `tests/test_help_content.py`
- Test: `tests/test_agent_input_plugins.py`
- Test: `tests/test_desktop_qt_help.py`

- [x] **Step 1: Write failing search and folder-connector tests**

```python
def test_help_search_finds_textractor_guidance():
    index = HelpIndex.load_default()
    results = index.search("Textractor")
    assert results
    assert results[0].topic_id == "connectors"


def test_folder_connector_reads_utf8_text_once(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    inbox.joinpath("scene.txt").write_text("こんにちは", encoding="utf-8")
    plugin = FolderInboxInputPlugin(inbox)

    first = plugin.capture()
    second = plugin.capture()

    assert [item.text for item in first] == ["こんにちは"]
    assert second == []
```

- [x] **Step 2: Verify RED**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_help_content.py tests\test_agent_input_plugins.py tests\test_desktop_qt_help.py
```

- [x] **Step 3: Implement indexed Markdown help**

Load packaged Markdown into `HelpTopic(topic_id, title, keywords, markdown)`. Search case-folded title, keywords, and body, rank exact title/keyword matches first, and render selected content in a read-only Qt text browser. Package the Markdown files as PyInstaller data.

- [x] **Step 4: Implement safe connector boundaries**

Add a folder inbox plugin with UTF-8 text/JSON support, content hash de-duplication, maximum payload size, and explicit archive/error directories. Keep clipboard/Hook buffer support. Document Textractor pipe/extension output, LunaTranslator clipboard/file output, and GalTransl project-file exchange without copying or embedding GPL project code.

- [x] **Step 5: Verify and commit**

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
E:\Ana\python.exe -m pytest -q tests\test_help_content.py tests\test_agent_input_plugins.py tests\test_desktop_qt_help.py
git add src/consensus_translation/help_content.py src/consensus_translation/agent_input_plugins.py src/consensus_translation/desktop_qt/pages/help.py src/consensus_translation/desktop_qt/pages/connectors.py docs/help tests
git commit -m "feat: add searchable help and connector inbox"
```

### Task 7: Reproducible E-drive runtime installer

**Files:**
- Modify: `install_optional_runtimes.ps1`
- Create: `src/consensus_translation/runtime_manifest.py`
- Create: `tests/test_runtime_manifest.py`
- Modify: `tests/test_optional_runtime_installer.py`

- [x] **Step 1: Write failing manifest and script contract tests**

```python
def test_runtime_manifest_requires_all_ocr_languages():
    manifest = RuntimeManifest.default()
    assert manifest.ocr_languages == ("eng", "jpn", "chi_sim", "chi_tra")
    assert manifest.comet_model == "Unbabel/wmt22-comet-da"
    assert all(download.sha256 for download in manifest.downloads)


def test_runtime_manifest_rejects_non_e_development_root():
    with pytest.raises(ValueError, match="E drive"):
        RuntimeManifest.default().validate_development_root(Path("C:/runtime"))
```

- [x] **Step 2: Verify RED**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_runtime_manifest.py tests\test_optional_runtime_installer.py
```

- [x] **Step 3: Implement verified download manifest and script parameters**

Add `-RuntimeRoot`, `-DownloadTesseract`, `-DownloadComet`, `-DownloadModel`, and `-OfflineCache`. In development mode reject roots outside E. In installed mode accept the installer-supplied `{app}\runtime` root. Every download uses HTTPS, expected size/SHA256, `.partial` files, and atomic rename.

The generated `runtime-settings.json` contains relative paths when under the install root so moving a portable directory does not retain stale absolute paths.

- [x] **Step 4: Verify script dry-run and commit**

```powershell
powershell -ExecutionPolicy Bypass -File .\install_optional_runtimes.ps1 -RuntimeRoot 'E:\Cn-Jp Translate\.runtime' -WhatIf
E:\Ana\python.exe -m pytest -q tests\test_runtime_manifest.py tests\test_optional_runtime_installer.py
git add install_optional_runtimes.ps1 src/consensus_translation/runtime_manifest.py tests/test_runtime_manifest.py tests/test_optional_runtime_installer.py
git commit -m "feat: add verified E-drive runtime installer"
```

### Task 8: Install and verify Tesseract and COMET on E

**Files:**
- Generated only: `.runtime/**` (gitignored)
- Create: `scripts/verify_optional_runtimes.py`
- Create: `tests/test_verify_optional_runtimes.py`
- Modify: `docs/user_manual_zh.md`

- [x] **Step 1: Write a failing verifier test**

```python
def test_verifier_reports_missing_japanese_language(tmp_path):
    result = verify_runtime(
        RuntimeLayout.from_roots(tmp_path),
        command_runner=fake_tesseract_with_languages("eng", "osd"),
    )
    assert result.ok is False
    assert result.missing_ocr_languages == ("jpn", "chi_sim", "chi_tra")
```

- [x] **Step 2: Implement the verifier**

The verifier runs Tesseract `--version`/`--list-langs`, OCRs generated English/Japanese/Chinese fixture images, runs `comet-score --help`, loads the configured COMET model from the E cache, scores one local source/hypothesis/reference sample, and writes `.runtime/runtime-verification.json`.

- [x] **Step 3: Download into E and verify**

```powershell
powershell -ExecutionPolicy Bypass -File .\install_optional_runtimes.ps1 -RuntimeRoot 'E:\Cn-Jp Translate\.runtime' -DownloadTesseract -DownloadComet -DownloadModel
E:\Ana\python.exe scripts\verify_optional_runtimes.py --runtime-root 'E:\Cn-Jp Translate\.runtime'
```

Expected: all four OCR languages present; OCR fixtures pass; COMET CLI/model/sample score pass. Network or registry failures must be retried with explicit authorization, never redirected to C.

- [x] **Step 4: Run tests and commit source evidence**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_verify_optional_runtimes.py tests\test_agent_evaluators.py
git add scripts/verify_optional_runtimes.py tests/test_verify_optional_runtimes.py docs/user_manual_zh.md
git commit -m "test: verify OCR and COMET runtime capabilities"
```

### Task 9: PyInstaller Qt portable build

**Files:**
- Create: `packaging/desktop_agent_qt.spec`
- Create: `build_desktop_qt.ps1`
- Modify: `requirements-desktop.txt`
- Modify: `src/consensus_translation/agent_packaging.py`
- Test: `tests/test_desktop_qt_packaging.py`

- [x] **Step 1: Write failing packaging tests**

```python
def test_qt_spec_packages_help_and_release_documents():
    spec = (ROOT / "packaging" / "desktop_agent_qt.spec").read_text(encoding="utf-8")
    assert "consensus_translation.desktop_qt.application" in spec
    assert "docs/help" in spec
    assert "MODEL_LICENSES.md" in spec
    assert "console=False" in spec
```

- [x] **Step 2: Verify RED, implement spec, then build**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_packaging.py
powershell -ExecutionPolicy Bypass -File .\build_desktop_qt.ps1
```

The spec uses the Qt application module, includes help/license docs, excludes Streamlit/Tkinter-only runtime where safe, and keeps heavy translation/COMET dependencies external. The build script runs packaging preflight and writes only under workspace `build`/`dist`.

- [x] **Step 3: Run packaged installed diagnostics and smoke**

Use `Start-Process -Wait -WindowStyle Hidden` for the windowed executable:

```powershell
$exe = 'dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe'
Start-Process -FilePath $exe -ArgumentList '--diagnostics','--diagnostics-mode','installed','--install-root','dist\ConsensusTranslationAgent','--report-json','.acceptance\qt-packaged-diagnostics.json' -Wait -WindowStyle Hidden
Start-Process -FilePath $exe -ArgumentList '--local-smoke','--acceptance-dir','.acceptance\qt-packaged-smoke' -Wait -WindowStyle Hidden
```

- [x] **Step 4: Verify and commit**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_desktop_qt_packaging.py tests\test_desktop_packaging.py
git add packaging/desktop_agent_qt.spec build_desktop_qt.ps1 requirements-desktop.txt src/consensus_translation/agent_packaging.py tests/test_desktop_qt_packaging.py
git commit -m "build: package PySide6 desktop application"
```

### Task 10: Inno Setup installer with selectable directory and shortcuts

**Files:**
- Create: `packaging/installer/ConsensusTranslationAgent.iss`
- Create: `build_installer.ps1`
- Create: `tests/test_installer_definition.py`
- Modify: `.gitignore`

- [x] **Step 1: Write failing installer contract tests**

```python
def test_installer_supports_directory_and_desktop_shortcut():
    source = (ROOT / "packaging" / "installer" / "ConsensusTranslationAgent.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in source
    assert "DefaultDirName={localappdata}\\Programs\\ConsensusTranslationAgent" in source
    assert 'Name: "desktopicon"' in source
    assert 'Name: "{autodesktop}\\共识翻译 Agent"' in source
    assert 'Filename: "{app}\\ConsensusTranslationAgent\\ConsensusTranslationAgent.exe"' in source
    assert 'Source: "{#RuntimePayload}\\*"; DestDir: "{app}\\runtime"' in source
```

- [x] **Step 2: Verify RED**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_installer_definition.py
```

- [x] **Step 3: Install Inno Setup under E and implement installer**

Search C first, then E. If ISCC is absent, download the official installer to `E:\Cn-Jp Translate\.runtime\downloads`, verify its publisher/hash, and install compiler files to `E:\Cn-Jp Translate\.runtime\InnoSetup6`.

The `.iss` file uses one stable AppId, selectable `DefaultDirName`, a `desktopicon` task, start-menu and uninstall entries, license/privacy pages, app/help/runtime payloads, upgrade-safe overwrite rules, and optional data removal on uninstall. `build_installer.ps1` discovers ISCC C then E and never installs tools to C automatically.

- [x] **Step 4: Build standard and full installers**

```powershell
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -RuntimePayload 'E:\Cn-Jp Translate\.runtime' -Channel full
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Channel standard
```

- [x] **Step 5: Verify installer metadata and commit**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_installer_definition.py
git add packaging/installer/ConsensusTranslationAgent.iss build_installer.ps1 tests/test_installer_definition.py .gitignore
git commit -m "build: add selectable Windows installer and shortcuts"
```

### Task 11: Installer acceptance, release manifests, and commercial/open-source docs

**Files:**
- Create: `scripts/verify_installed_release.ps1`
- Create: `docs/release_checklist_zh.md`
- Modify: `src/consensus_translation/agent_release.py`
- Modify: `build_desktop_release.ps1`
- Modify: `README.md`
- Modify: `docs/user_manual_zh.md`
- Test: `tests/test_agent_release.py`

- [ ] **Step 1: Write failing release-manifest tests**

```python
def test_release_manifest_records_installer_and_license_profile(tmp_path):
    build = build_desktop_release_package(
        tmp_path,
        version="2026.06.18",
        channel="full",
        license_profile="commercial-safe",
        installer_path=tmp_path / "ConsensusTranslationAgent-Setup.exe",
    )
    manifest = json.loads(build.manifest_path.read_text(encoding="utf-8"))
    assert manifest["license_profile"] == "commercial-safe"
    assert manifest["artifacts"]["installer"]["sha256"]
    assert "code-signing" in manifest["not_included"]
```

- [ ] **Step 2: Implement release evidence**

Manifest records exe, portable ZIP, standard/full installer, hashes, runtime versions, OCR languages, COMET model, engine/license profile, included help/docs, unsigned status, and verification report paths. The release checklist distinguishes automated evidence from target-machine manual GUI/signing checks.

- [ ] **Step 3: Install to a non-default E path and verify**

Use an isolated path such as `E:\Cn-Jp Translate\.acceptance\installed-release` and silent installer parameters that match interactive choices. Verify files, runtime root, data root, desktop shortcut target, start-menu entry, installed diagnostics, local smoke, help resources, and uninstaller. Do not delete outside `.acceptance`; verify resolved paths before uninstall cleanup.

- [ ] **Step 4: Run focused tests and commit**

```powershell
E:\Ana\python.exe -m pytest -q tests\test_agent_release.py tests\test_installer_definition.py
git add scripts/verify_installed_release.ps1 docs/release_checklist_zh.md src/consensus_translation/agent_release.py build_desktop_release.ps1 README.md docs/user_manual_zh.md tests/test_agent_release.py
git commit -m "release: add installer acceptance and release evidence"
```

### Task 12: Full completion audit and final release build

**Files:**
- Modify: `docs/worklog_zh.md`
- Generated only: `release/**`, `.acceptance/**`

- [ ] **Step 1: Run the full hermetic test suite**

```powershell
E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime\final-release'
```

Expected: zero failures. Record warning count and exact warning causes; do not hide new warnings.

- [ ] **Step 2: Build all deliverables**

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop_release.ps1
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -RuntimePayload 'E:\Cn-Jp Translate\.runtime' -Channel full
```

- [ ] **Step 3: Run source, portable, and installed acceptance**

```powershell
powershell -ExecutionPolicy Bypass -File .\run_desktop_acceptance.ps1 -OutputDir '.acceptance\source-final'
powershell -ExecutionPolicy Bypass -File .\scripts\verify_installed_release.ps1 -InstallerPath 'release\ConsensusTranslationAgent-Setup.exe' -InstallDir 'E:\Cn-Jp Translate\.acceptance\installed-final'
```

Also run Qt offscreen workflow tests and one visible GUI launch/manual interaction pass. Real remote providers remain disabled; use static provider contract tests only.

- [ ] **Step 4: Audit the design requirements line by line**

For every item in `docs/superpowers/specs/2026-06-18-commercial-desktop-agent-release-design.md` section 9, link the authoritative report, command output, artifact, or manual evidence. Any missing evidence keeps the goal incomplete.

- [ ] **Step 5: Update worklog and commit**

```powershell
git add docs/worklog_zh.md
git commit -m "docs: record commercial desktop release verification"
```

- [ ] **Step 6: Finish the development branch**

Use `superpowers:requesting-code-review`, fix actionable findings, rerun all release gates, then use `superpowers:finishing-a-development-branch` to present integration options. Do not push, merge, or publish externally without user authorization.
