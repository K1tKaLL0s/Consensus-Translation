# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH).resolve()
if not (project_root / "src").exists():
    project_root = project_root.parent
src_dir = project_root / "src"
entrypoint = src_dir / "consensus_translation" / "desktop_qt" / "application.py"

block_cipher = None

datas = [
    (str(project_root / "README.md"), "."),
    (str(project_root / "LICENSE"), "."),
    (str(project_root / "MODEL_LICENSES.md"), "."),
    (str(project_root / "docs" / "help"), "docs/help"),
    (str(project_root / "docs/user_manual_zh.md"), "docs"),
    (str(project_root / "docs/desktop_agent_core_zh.md"), "docs"),
    (str(project_root / "docs/desktop_agent_research_zh.md"), "docs"),
    (
        str(project_root / "UI design" / "High-Fidelity Translation Software UI" / "dist"),
        "react-ui-dist",
    ),
]

a = Analysis(
    [str(entrypoint)],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWidgets",
        "consensus_translation.agent_acceptance",
        "consensus_translation.agent_artifacts",
        "consensus_translation.agent_context",
        "consensus_translation.agent_continuation",
        "consensus_translation.agent_credentials",
        "consensus_translation.agent_diagnostics",
        "consensus_translation.agent_evaluators",
        "consensus_translation.agent_input_plugins",
        "consensus_translation.agent_inputs",
        "consensus_translation.agent_packaging",
        "consensus_translation.agent_preflight",
        "consensus_translation.agent_project",
        "consensus_translation.agent_provider_config",
        "consensus_translation.agent_provider_smoke",
        "consensus_translation.agent_providers",
        "consensus_translation.agent_runtime",
        "consensus_translation.agent_store",
        "consensus_translation.agent_workflows",
        "consensus_translation.desktop_agent_app",
        "consensus_translation.desktop_qt.application",
        "consensus_translation.desktop_qt.application_service",
        "consensus_translation.desktop_qt.main_window",
        "consensus_translation.desktop_qt.navigation",
        "consensus_translation.desktop_qt.pages.connectors",
        "consensus_translation.desktop_qt.pages.diagnostics",
        "consensus_translation.desktop_qt.pages.help",
        "consensus_translation.desktop_qt.pages.home",
        "consensus_translation.desktop_qt.pages.lexicon",
        "consensus_translation.desktop_qt.pages.projects",
        "consensus_translation.desktop_qt.pages.providers",
        "consensus_translation.desktop_qt.pages.workbench",
        "consensus_translation.desktop_qt.react_workspace",
        "consensus_translation.desktop_qt.theme",
        "consensus_translation.help_content",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "PIL",
        "docutils",
        "jedi",
        "matplotlib",
        "numpy",
        "pandas",
        "pytest",
        "pygments",
        "rich",
        "streamlit",
        "tkinter",
        "torch",
        "transformers",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ConsensusTranslationAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ConsensusTranslationAgent",
)
