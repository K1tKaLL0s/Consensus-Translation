from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_project import DesktopProjectProfile
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.desktop_agent_app import DesktopAgentConfig, DesktopAgentController


def test_sqlite_store_persists_desktop_project_profile(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    profile = DesktopProjectProfile(
        project_id="novel-a",
        source_lang="zh",
        target_lang="ja",
        topic="western_myth",
        mode="learning",
        max_context_tokens=8192,
        reserved_output_tokens=2048,
        api_enabled=True,
        budget_limit=3.5,
        require_remote_confirmation=True,
        allow_training_upload=True,
        training_file="training.md",
        validation_file="validation.md",
        evaluator_kind="comet",
        tesseract_command=r"E:\runtime\Tesseract-OCR\tesseract.exe",
        ocr_language="jpn+eng",
        comet_command=r"E:\runtime\comet-env\Scripts\comet-score.exe",
        comet_model="Unbabel/wmt22-comet-da",
        comet_model_storage_path=r"E:\runtime\comet-models",
        recent_files=["chapter-01.txt", "chapter-02.docx"],
    )

    store.save_project_profile(profile)

    assert store.get_project_profile("novel-a") == profile
    assert store.get_project_profile("missing-project") is None


def test_desktop_controller_loads_and_saves_project_profile(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    profile = DesktopProjectProfile(
        project_id="novel-a",
        source_lang="en",
        target_lang="zh",
        topic="science",
        mode="self_decision",
        max_context_tokens=4096,
        reserved_output_tokens=512,
        api_enabled=True,
        budget_limit=2.0,
        require_remote_confirmation=False,
        allow_training_upload=True,
        training_file="training.txt",
        validation_file="validation.txt",
        evaluator_kind="comet",
        tesseract_command=r"E:\Tesseract-OCR\tesseract.exe",
        ocr_language="jpn+eng",
        comet_command=r"E:\comet-env\Scripts\comet-score.exe",
        comet_model="Unbabel/wmt22-comet-da",
        comet_model_storage_path=r"E:\comet-models",
        recent_files=["chapter.md"],
    )
    store.save_project_profile(profile)
    controller = DesktopAgentController(store=store, project_id="novel-a")

    loaded = controller.load_project_profile()

    assert loaded == profile
    assert controller.config == DesktopAgentConfig(
        source_lang="en",
        target_lang="zh",
        topic="science",
        mode="self_decision",
        max_context_tokens=4096,
        reserved_output_tokens=512,
        api_enabled=True,
        budget_limit=2.0,
        require_remote_confirmation=False,
        allow_training_upload=True,
        training_file="training.txt",
        validation_file="validation.txt",
        evaluator_kind="comet",
        tesseract_command=r"E:\Tesseract-OCR\tesseract.exe",
        ocr_language="jpn+eng",
        comet_command=r"E:\comet-env\Scripts\comet-score.exe",
        comet_model="Unbabel/wmt22-comet-da",
        comet_model_storage_path=r"E:\comet-models",
    )
    controller.config = DesktopAgentConfig(topic="history", max_context_tokens=2048)
    saved = controller.save_project_profile(recent_files=["new.txt"])
    assert saved.topic == "history"
    assert saved.recent_files == ["new.txt"]
    assert store.get_project_profile("novel-a") == saved


def test_desktop_controller_records_recent_file_after_translation(tmp_path):
    source_file = tmp_path / "chapter.txt"
    source_file.write_text("alpha beta", encoding="utf-8")
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    controller = DesktopAgentController(
        config=DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            allow_mock_providers=True,
        ),
        store=store,
        project_id="novel-a",
    )

    controller.translate_file(source_file)

    profile = store.get_project_profile("novel-a")
    assert profile is not None
    assert profile.recent_files == [str(source_file)]
