from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.agent_diagnostics import CommandResult
from consensus_translation.agent_runtime import RuntimeLayout
from scripts.verify_optional_runtimes import _font_candidates, verify_runtime


def fake_tesseract_with_languages(*languages: str):
    def runner(command):
        if command[-1] == "--version":
            return CommandResult(0, "tesseract 5.5.0", "")
        if command[-1] == "--list-langs":
            return CommandResult(
                0,
                "List of available languages:\n" + "\n".join(languages),
                "",
            )
        if "--help" in command:
            return CommandResult(0, "comet-score help", "")
        return CommandResult(0, "ok", "")

    return runner


def test_verifier_reports_missing_japanese_language(tmp_path):
    result = verify_runtime(
        RuntimeLayout.from_roots(tmp_path),
        command_runner=fake_tesseract_with_languages("eng", "osd"),
        run_ocr_fixtures=False,
        run_comet_sample=False,
    )

    assert result.ok is False
    assert result.missing_ocr_languages == ("jpn", "chi_sim", "chi_tra")


def test_verifier_passes_required_language_and_comet_cli_checks(tmp_path):
    result = verify_runtime(
        RuntimeLayout.from_roots(tmp_path),
        command_runner=fake_tesseract_with_languages("eng", "jpn", "chi_sim", "chi_tra"),
        run_ocr_fixtures=False,
        run_comet_sample=False,
    )

    assert result.ok is True
    assert result.missing_ocr_languages == ()
    assert result.comet_cli_ok is True


def test_font_candidates_search_windows_fonts_before_e_drive(tmp_path):
    c_fonts = tmp_path / "C" / "Windows" / "Fonts"
    e_fonts = tmp_path / "E" / "Fonts"

    candidates = _font_candidates(
        "jpn",
        windows_font_dir=c_fonts,
        e_font_roots=(e_fonts,),
    )

    assert candidates[0] == c_fonts / "NotoSansJP-VF.ttf"
    assert c_fonts / "meiryo.ttc" in candidates
    assert e_fonts / "NotoSansJP-VF.ttf" in candidates
    assert candidates.index(c_fonts / "YuGothR.ttc") < candidates.index(
        e_fonts / "NotoSansJP-VF.ttf"
    )
