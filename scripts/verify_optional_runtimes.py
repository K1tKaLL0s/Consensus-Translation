from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.agent_diagnostics import CommandResult
from consensus_translation.agent_evaluators import (
    EvaluationRequest,
    ExternalCometTranslationEvaluator,
)
from consensus_translation.agent_runtime import RuntimeLayout
from consensus_translation.runtime_manifest import RuntimeManifest


CommandRunner = Callable[[list[str]], CommandResult]


FONT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "eng": (
        "arial.ttf",
        "segoeui.ttf",
    ),
    "jpn": (
        "NotoSansJP-VF.ttf",
        "meiryo.ttc",
        "meiryob.ttc",
        "msgothic.ttc",
        "YuGothM.ttc",
        "YuGothR.ttc",
    ),
    "chi_sim": (
        "NotoSansSC-VF.ttf",
        "msyh.ttc",
        "msyhbd.ttc",
        "simhei.ttf",
        "simsun.ttc",
    ),
    "chi_tra": (
        "mingliub.ttc",
        "NotoSansSC-VF.ttf",
        "msyh.ttc",
        "simsun.ttc",
    ),
}


def _configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _font_candidates(
    language: str,
    windows_font_dir: Path | None = None,
    e_font_roots: tuple[Path, ...] | None = None,
) -> tuple[Path, ...]:
    windows_fonts = windows_font_dir or (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    )
    e_roots = e_font_roots or (
        Path(r"E:\Fonts"),
        Path(r"E:\Windows\Fonts"),
        ROOT / "assets" / "fonts",
    )
    names = FONT_CANDIDATES.get(language, FONT_CANDIDATES["eng"])
    roots = (windows_fonts, *e_roots)
    return tuple(root / name for root in roots for name in names)


def _load_fixture_font(language: str, size: int = 72):
    from PIL import ImageFont

    for path in _font_candidates(language):
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size), path
        except OSError:
            continue
    return ImageFont.load_default(), None


@dataclass(frozen=True)
class RuntimeVerificationResult:
    ok: bool
    runtime_root: Path
    tesseract_version_ok: bool
    tesseract_version: str
    ocr_languages: tuple[str, ...]
    missing_ocr_languages: tuple[str, ...]
    ocr_fixture_ok: bool
    comet_cli_ok: bool
    comet_model_ok: bool
    comet_score: float | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["runtime_root"] = str(self.runtime_root)
        return payload


def _run_command(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, str(exc.stdout or ""), str(exc.stderr or exc))
    return CommandResult(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _parse_tesseract_languages(stdout: str) -> tuple[str, ...]:
    languages: list[str] = []
    for line in stdout.splitlines():
        value = line.strip()
        if not value or value.lower().startswith("list of available languages"):
            continue
        languages.append(value)
    return tuple(sorted(set(languages)))


def _verify_ocr_fixtures(
    layout: RuntimeLayout,
    command_runner: CommandRunner,
) -> tuple[bool, tuple[str, ...]]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False, ("Pillow is required to generate OCR verification images",)

    samples = {
        "eng": "HELLO 123",
        "jpn": "こんにちは",
        "chi_sim": "简体中文",
        "chi_tra": "繁體中文",
    }
    errors: list[str] = []
    with TemporaryDirectory(prefix="consensus-ocr-fixtures-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        for language, text in samples.items():
            font, font_path = _load_fixture_font(language)
            if language != "eng" and font_path is None:
                errors.append(f"no CJK font found for OCR fixture: {language}")
                continue
            image_path = temp_dir / f"{language}.png"
            image = Image.new("RGB", (640, 160), "white")
            draw = ImageDraw.Draw(image)
            draw.text((24, 38), text, fill="black", font=font)
            image.save(image_path)
            result = command_runner(
                [
                    str(layout.tesseract_command),
                    str(image_path),
                    "stdout",
                    "-l",
                    language,
                    "--psm",
                    "7",
                    "--dpi",
                    "300",
                ]
            )
            output = result.stdout.strip()
            if result.returncode != 0 or not output:
                errors.append(
                    f"ocr fixture failed for {language}: {result.stderr or result.stdout}"
                )
    return (not errors, tuple(errors))


def _verify_comet_sample(
    layout: RuntimeLayout,
    command_runner: CommandRunner,
) -> tuple[bool, float | None, tuple[str, ...]]:
    manifest = RuntimeManifest.default()

    def runner(command: list[str], timeout: float):
        _ = timeout
        return command_runner(command)

    evaluator = ExternalCometTranslationEvaluator(
        command=str(layout.comet_command),
        model_name=manifest.comet_model,
        model_storage_path=layout.comet_model_root,
        runner=runner,
    )
    try:
        result = evaluator.evaluate(
            EvaluationRequest(
                source_text="hello",
                candidate_text="こんにちは",
                reference_text="こんにちは",
                source_lang="en",
                target_lang="ja",
                topic="runtime-verification",
                round_index=1,
            )
        )
    except RuntimeError as exc:
        return False, None, (str(exc),)
    return True, float(result.score), ()


def verify_runtime(
    layout: RuntimeLayout,
    command_runner: CommandRunner | None = None,
    required_ocr_languages: tuple[str, ...] | None = None,
    run_ocr_fixtures: bool = True,
    run_comet_sample: bool = True,
) -> RuntimeVerificationResult:
    runner = command_runner or _run_command
    manifest = RuntimeManifest.default()
    required_languages = required_ocr_languages or manifest.ocr_languages
    errors: list[str] = []
    warnings: list[str] = []

    version = runner([str(layout.tesseract_command), "--version"])
    tesseract_version_ok = version.returncode == 0
    tesseract_version = (version.stdout or version.stderr).splitlines()[0].strip() if (
        version.stdout or version.stderr
    ) else ""
    if not tesseract_version_ok:
        errors.append(f"tesseract --version failed: {version.stderr or version.stdout}")

    languages_result = runner([str(layout.tesseract_command), "--list-langs"])
    ocr_languages = (
        _parse_tesseract_languages(languages_result.stdout)
        if languages_result.returncode == 0
        else ()
    )
    if languages_result.returncode != 0:
        errors.append(
            f"tesseract --list-langs failed: {languages_result.stderr or languages_result.stdout}"
        )
    missing = tuple(
        language for language in required_languages if language not in ocr_languages
    )
    if missing:
        errors.append("missing OCR languages: " + ", ".join(missing))

    ocr_fixture_ok = not run_ocr_fixtures
    if run_ocr_fixtures and not missing and tesseract_version_ok:
        ocr_fixture_ok, fixture_errors = _verify_ocr_fixtures(layout, runner)
        errors.extend(fixture_errors)
    elif run_ocr_fixtures and missing:
        warnings.append("OCR fixture verification skipped because languages are missing")

    comet_help = runner([str(layout.comet_command), "--help"])
    comet_cli_ok = comet_help.returncode == 0
    if not comet_cli_ok:
        errors.append(f"comet-score --help failed: {comet_help.stderr or comet_help.stdout}")

    comet_model_ok = not run_comet_sample
    comet_score: float | None = None
    if run_comet_sample and comet_cli_ok:
        comet_model_ok, comet_score, comet_errors = _verify_comet_sample(layout, runner)
        errors.extend(comet_errors)
    elif run_comet_sample and not comet_cli_ok:
        warnings.append("COMET sample verification skipped because CLI is unavailable")

    ok = (
        tesseract_version_ok
        and not missing
        and ocr_fixture_ok
        and comet_cli_ok
        and comet_model_ok
    )
    return RuntimeVerificationResult(
        ok=ok,
        runtime_root=layout.runtime_root,
        tesseract_version_ok=tesseract_version_ok,
        tesseract_version=tesseract_version,
        ocr_languages=ocr_languages,
        missing_ocr_languages=missing,
        ocr_fixture_ok=ocr_fixture_ok,
        comet_cli_ok=comet_cli_ok,
        comet_model_ok=comet_model_ok,
        comet_score=comet_score,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _layout_from_runtime_root(runtime_root: str | Path) -> RuntimeLayout:
    runtime = Path(runtime_root).resolve()
    install = runtime.parent
    return RuntimeLayout(
        install_root=install,
        runtime_root=runtime,
        data_root=install / "data",
        tesseract_command=runtime / "Tesseract-OCR" / "tesseract.exe",
        comet_command=runtime / "comet-env" / "Scripts" / "comet-score.exe",
        comet_model_root=runtime / "comet-models",
    )


def write_verification_report(
    result: RuntimeVerificationResult,
    report_path: str | Path,
) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            result.to_json_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    _configure_output_encoding()
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--report-json")
    parser.add_argument("--skip-ocr-fixtures", action="store_true")
    parser.add_argument("--skip-comet-sample", action="store_true")
    args = parser.parse_args(argv)

    layout = _layout_from_runtime_root(args.runtime_root)
    result = verify_runtime(
        layout,
        run_ocr_fixtures=not args.skip_ocr_fixtures,
        run_comet_sample=not args.skip_comet_sample,
    )
    report_path = args.report_json or (layout.runtime_root / "runtime-verification.json")
    write_verification_report(result, report_path)
    print(f"runtime verification: {'ok' if result.ok else 'failed'}")
    print(f"runtime root: {layout.runtime_root}")
    if result.missing_ocr_languages:
        print("missing OCR languages: " + ", ".join(result.missing_ocr_languages))
    if result.errors:
        for error in result.errors:
            print(f"error: {error}")
    if result.warnings:
        for warning in result.warnings:
            print(f"warning: {warning}")
    print(f"report: {report_path}")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
