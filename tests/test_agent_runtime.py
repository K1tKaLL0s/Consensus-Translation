from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import consensus_translation.agent_runtime as agent_runtime
from consensus_translation.agent_runtime import (
    RuntimeLayout,
    resolve_comet_command,
    resolve_comet_model_storage_path,
    resolve_tesseract_command,
)


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
    assert layout.comet_model_root == (
        install_root / "runtime" / "comet-models"
    ).resolve()
    assert layout.data_root == (install_root / "data").resolve()


def test_runtime_layout_reads_legacy_project_runtime_settings(tmp_path):
    project_root = tmp_path / "project"
    runtime_root = project_root / ".runtime"
    runtime_root.mkdir(parents=True)
    runtime_root.joinpath("runtime-settings.json").write_text(
        json.dumps(
            {
                "runtime_root": str(runtime_root),
                "tesseract_command": str(
                    runtime_root / "Tesseract-OCR" / "tesseract.exe"
                ),
                "comet_command": str(
                    runtime_root / "comet-env" / "Scripts" / "comet-score.exe"
                ),
                "comet_model_storage_path": str(runtime_root / "comet-models"),
            }
        ),
        encoding="utf-8",
    )

    layout = RuntimeLayout.discover(project_root=project_root)

    assert layout.runtime_root == runtime_root.resolve()
    assert layout.tesseract_command == (
        runtime_root / "Tesseract-OCR" / "tesseract.exe"
    ).resolve()
    assert layout.comet_command == (
        runtime_root / "comet-env" / "Scripts" / "comet-score.exe"
    ).resolve()
    assert layout.comet_model_root == (runtime_root / "comet-models").resolve()


def test_tesseract_runtime_prefers_c_candidate_before_e_candidate(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    c_command = tmp_path / "c" / "Tesseract-OCR" / "tesseract.exe"
    e_command = tmp_path / "e" / "Tesseract-OCR" / "tesseract.exe"
    c_command.parent.mkdir(parents=True)
    e_command.parent.mkdir(parents=True)
    c_command.write_bytes(b"c")
    e_command.write_bytes(b"e")

    resolved = resolve_tesseract_command(
        project_root=tmp_path / "project",
        candidate_paths=[c_command, e_command],
        which_fn=lambda name: None,
    )

    assert resolved == str(c_command)


def test_tesseract_runtime_falls_back_to_e_candidate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    e_command = tmp_path / "e" / "Tesseract-OCR" / "tesseract.exe"
    e_command.parent.mkdir(parents=True)
    e_command.write_bytes(b"e")

    resolved = resolve_tesseract_command(
        project_root=tmp_path / "project",
        candidate_paths=[tmp_path / "c" / "tesseract.exe", e_command],
        which_fn=lambda name: None,
    )

    assert resolved == str(e_command)


def test_comet_runtime_uses_explicit_sidecar_command(tmp_path):
    command = tmp_path / "comet-env" / "Scripts" / "comet-score.exe"
    command.parent.mkdir(parents=True)
    command.write_bytes(b"exe")

    resolved = resolve_comet_command(
        configured=str(command),
        candidate_paths=[],
        which_fn=lambda name: None,
    )

    assert resolved == str(command)


def test_comet_model_cache_defaults_next_to_sidecar_environment(tmp_path):
    command = tmp_path / "runtime" / "comet-env" / "Scripts" / "comet-score.exe"
    command.parent.mkdir(parents=True)
    command.write_bytes(b"exe")

    resolved = resolve_comet_model_storage_path(
        configured=None,
        comet_command=str(command),
        project_root=tmp_path / "project",
    )

    assert resolved == str(tmp_path / "runtime" / "comet-models")


def test_project_runtime_settings_override_global_c_to_e_discovery(tmp_path):
    project_root = tmp_path / "project"
    settings_dir = project_root / ".runtime"
    settings_dir.mkdir(parents=True)
    e_tesseract = tmp_path / "e" / "Tesseract-OCR" / "tesseract.exe"
    e_comet = tmp_path / "e" / "comet-env" / "Scripts" / "comet-score.exe"
    e_models = tmp_path / "e" / "comet-models"
    settings_dir.joinpath("runtime-settings.json").write_text(
        json.dumps(
            {
                "tesseract_command": str(e_tesseract),
                "comet_command": str(e_comet),
                "comet_model_storage_path": str(e_models),
            }
        ),
        encoding="utf-8",
    )
    c_tesseract = tmp_path / "c" / "Tesseract-OCR" / "tesseract.exe"
    c_tesseract.parent.mkdir(parents=True)
    c_tesseract.write_bytes(b"c")

    assert resolve_tesseract_command(
        project_root=project_root,
        candidate_paths=[c_tesseract],
        which_fn=lambda name: None,
    ) == str(e_tesseract)
    assert resolve_comet_command(
        project_root=project_root,
        candidate_paths=[],
        which_fn=lambda name: None,
    ) == str(e_comet)
    assert resolve_comet_model_storage_path(
        configured=None,
        comet_command=str(e_comet),
        project_root=project_root,
    ) == str(e_models)


def test_packaged_app_discovers_runtime_settings_beside_release_root(
    tmp_path,
    monkeypatch,
):
    release_root = tmp_path / "portable"
    app_dir = release_root / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    fake_exe = app_dir / "ConsensusTranslationAgent.exe"
    fake_exe.write_bytes(b"exe")
    runtime_dir = release_root / ".runtime"
    runtime_dir.mkdir()
    tesseract = runtime_dir / "Tesseract-OCR" / "tesseract.exe"
    runtime_dir.joinpath("runtime-settings.json").write_text(
        json.dumps({"tesseract_command": str(tesseract)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_runtime.sys, "executable", str(fake_exe))
    monkeypatch.chdir(tmp_path / "elsewhere" if False else tmp_path)

    resolved = resolve_tesseract_command(
        project_root=app_dir / "_internal",
        candidate_paths=[],
        which_fn=lambda name: None,
    )

    assert resolved == str(tesseract)
