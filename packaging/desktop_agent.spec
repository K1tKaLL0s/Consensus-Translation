# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH).resolve()
if not (project_root / "src").exists():
    project_root = project_root.parent
src_dir = project_root / "src"
entrypoint = src_dir / "consensus_translation" / "desktop_agent_app.py"

block_cipher = None

a = Analysis(
    [str(entrypoint)],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "consensus_translation.agent_acceptance",
        "consensus_translation.agent_artifacts",
        "consensus_translation.agent_context",
        "consensus_translation.agent_continuation",
        "consensus_translation.agent_credentials",
        "consensus_translation.agent_diagnostics",
        "consensus_translation.agent_evaluators",
        "consensus_translation.agent_input_plugins",
        "consensus_translation.agent_inputs",
        "consensus_translation.agent_preflight",
        "consensus_translation.agent_providers",
        "consensus_translation.agent_runtime",
        "consensus_translation.agent_store",
        "consensus_translation.agent_workflows",
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
