import asyncio
from pathlib import Path
from uuid import uuid4

from src.core.agent_orchestrator import MAATCSOrchestrator
from src.services.file_ingest_service import FileIngestService
from src.services.glossary_service import normalize_source_name, parse_glossary_lines


class FileTaskService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.ingest = FileIngestService()

    def run_translate(self, upload_path: Path, source_declaration: str) -> dict[str, object]:
        normalized_source = normalize_source_name(source_declaration)
        text = self.ingest.read_text(upload_path)
        translated = self._translate_text(text=text, source_declaration=normalized_source)

        suffix = self.ingest.validate_path(upload_path)
        task_id = str(uuid4())
        output_path = self.output_dir / f"{task_id}{suffix}"
        self.ingest.write_text(output_path, translated)

        return {
            "task_id": task_id,
            "accepted": True,
            "source_declaration": normalized_source,
            "output_path": str(output_path),
            "text_length": len(text),
        }

    def _translate_text(self, text: str, source_declaration: str) -> str:
        if not text.strip():
            return ""

        orchestrator = MAATCSOrchestrator()
        state = asyncio.run(orchestrator.run(raw_text=text, source_declaration=source_declaration))
        consensus = state.get("consensus", {})
        winner = consensus.get("winner")
        if isinstance(winner, str) and winner.strip():
            return winner
        return text

    def run_glossary_import(self, upload_path: Path, source_declaration: str) -> dict[str, object]:
        normalized_source = normalize_source_name(source_declaration)
        text = self.ingest.read_text(upload_path)
        entries = parse_glossary_lines(text.splitlines())
        return {
            "accepted": True,
            "source_declaration": normalized_source,
            "imported_count": len(entries),
            "entries": entries,
        }
