from pathlib import Path

import src.services.file_task_service as file_task_module
from src.services.file_task_service import FileTaskService
from src.services.glossary_service import parse_glossary_lines


def test_parse_glossary_lines_supports_equal_comma_tab() -> None:
    lines = ["术语A=訳語A", "术语B,訳語B", "术语C\t訳語C"]

    entries = parse_glossary_lines(lines)

    assert entries == [
        {"term": "术语A", "translation": "訳語A"},
        {"term": "术语B", "translation": "訳語B"},
        {"term": "术语C", "translation": "訳語C"},
    ]


def test_parse_glossary_lines_fallback_whole_line() -> None:
    entries = parse_glossary_lines(["只是一行术语"])

    assert entries == [{"term": "只是一行术语", "translation": ""}]


def test_translate_usage_keeps_extension(tmp_path: Path) -> None:
    upload = tmp_path / "input.md"
    upload.write_text("原文", encoding="utf-8")

    class _FakeOrchestrator:
        async def run(self, raw_text: str, source_declaration: str) -> dict[str, object]:
            return {"consensus": {"winner": "译文"}}

    original_orchestrator = file_task_module.MAATCSOrchestrator
    file_task_module.MAATCSOrchestrator = _FakeOrchestrator
    try:
        result = FileTaskService(output_dir=tmp_path / "out").run_translate(
            upload,
            source_declaration="主题",
        )
    finally:
        file_task_module.MAATCSOrchestrator = original_orchestrator

    assert result["accepted"] is True
    assert str(result["output_path"]).endswith(".md")
    output_text = Path(str(result["output_path"])).read_text(encoding="utf-8")
    assert output_text == "译文"


def test_glossary_usage_returns_import_stats(tmp_path: Path) -> None:
    upload = tmp_path / "terms.txt"
    upload.write_text("术语A=訳語A\n术语B", encoding="utf-8")

    result = FileTaskService(output_dir=tmp_path / "out").run_glossary_import(
        upload,
        source_declaration="游戏王",
    )

    assert result["accepted"] is True
    assert result["imported_count"] == 2
    assert result["source_declaration"] == "游戏王"
