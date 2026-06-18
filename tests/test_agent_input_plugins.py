from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_input_plugins import (
    CapturedInput,
    FolderInboxInputPlugin,
    HookTextBufferPlugin,
    InputPluginRegistry,
    OcrImageInputPlugin,
    default_input_plugin_registry,
)


def test_ocr_image_plugin_uses_injected_ocr_function_and_metadata(tmp_path):
    image_path = tmp_path / "panel.png"
    image_path.write_bytes(b"fake image bytes")
    calls = []

    def fake_ocr(path: Path, lang: str) -> str:
        calls.append((path, lang))
        return "リヴァイアサン"

    plugin = OcrImageInputPlugin(ocr_fn=fake_ocr, default_lang="jpn+eng")

    capture = plugin.capture(path=image_path)

    assert capture == CapturedInput(
        input_ref=str(image_path),
        source_type="ocr",
        text="リヴァイアサン",
        metadata={"plugin_id": "ocr-image", "lang": "jpn+eng"},
        warnings=[],
    )
    assert calls == [(image_path, "jpn+eng")]


def test_ocr_image_plugin_rejects_unsupported_file_suffix(tmp_path):
    image_path = tmp_path / "panel.gif"
    image_path.write_bytes(b"fake image bytes")
    plugin = OcrImageInputPlugin(ocr_fn=lambda path, lang: "text")

    try:
        plugin.capture(path=image_path)
    except ValueError as exc:
        assert "unsupported ocr image type: .gif" in str(exc)
    else:
        raise AssertionError("unsupported image suffix should fail")


def test_hook_text_buffer_plugin_appends_captures_and_consumes_text():
    plugin = HookTextBufferPlugin()

    plugin.append_text("game.exe:1234", "第一行")
    plugin.append_text("game.exe:1234", "第二行")

    capture = plugin.capture(process_ref="game.exe:1234")
    empty_capture = plugin.capture(process_ref="game.exe:1234")

    assert capture.input_ref == "hook:game.exe:1234"
    assert capture.source_type == "hook"
    assert capture.text == "第一行\n第二行"
    assert capture.metadata == {
        "plugin_id": "hook-buffer",
        "process_ref": "game.exe:1234",
    }
    assert capture.warnings == []
    assert empty_capture.text == ""
    assert empty_capture.warnings == ["hook-buffer-empty"]


def test_input_plugin_registry_dispatches_plugins_by_id(tmp_path):
    image_path = tmp_path / "panel.jpg"
    image_path.write_bytes(b"fake image bytes")
    registry = InputPluginRegistry()
    registry.register(OcrImageInputPlugin(ocr_fn=lambda path, lang: "ocr text"))
    registry.register(HookTextBufferPlugin())

    capture = registry.capture("ocr-image", path=image_path, lang="jpn")

    assert registry.list_plugin_ids() == ["hook-buffer", "ocr-image"]
    assert capture.text == "ocr text"
    assert capture.metadata["lang"] == "jpn"


def test_default_input_plugin_registry_exposes_ocr_and_hook_plugins():
    registry = default_input_plugin_registry()

    assert registry.list_plugin_ids() == ["hook-buffer", "ocr-image"]


def test_default_input_plugin_registry_exposes_configured_folder_inbox(tmp_path):
    registry = default_input_plugin_registry(folder_inbox=tmp_path / "inbox")

    assert registry.list_plugin_ids() == [
        "folder-inbox",
        "hook-buffer",
        "ocr-image",
    ]


def test_folder_connector_reads_utf8_text_once(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    inbox.joinpath("scene.txt").write_text("こんにちは", encoding="utf-8")
    plugin = FolderInboxInputPlugin(inbox)

    first = plugin.capture()
    second = plugin.capture()

    assert [item.text for item in first] == ["こんにちは"]
    assert second == []


def test_folder_connector_reads_json_text_and_archives_file(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    inbox.joinpath("scene.json").write_text(
        '{"text": "json payload", "source": "tool"}',
        encoding="utf-8",
    )
    plugin = FolderInboxInputPlugin(inbox)

    captured = plugin.capture()

    assert [item.text for item in captured] == ["json payload"]
    assert captured[0].metadata["source"] == "tool"
    assert not (inbox / "scene.json").exists()
    assert (inbox / "archive" / "scene.json").exists()
