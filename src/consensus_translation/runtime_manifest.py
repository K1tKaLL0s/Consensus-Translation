from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeDownload:
    download_id: str
    url: str
    filename: str
    expected_size: int
    sha256: str
    target_subdir: str


@dataclass(frozen=True)
class RuntimeManifest:
    tesseract_version: str
    ocr_languages: tuple[str, ...]
    comet_package: str
    comet_model: str
    downloads: tuple[RuntimeDownload, ...]

    @classmethod
    def default(cls) -> "RuntimeManifest":
        tessdata_base = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main"
        return cls(
            tesseract_version="5.5.0.20241111",
            ocr_languages=("eng", "jpn", "chi_sim", "chi_tra"),
            comet_package="unbabel-comet==2.2.7",
            comet_model="Unbabel/wmt22-comet-da",
            downloads=(
                RuntimeDownload(
                    download_id="tesseract-installer",
                    url=(
                        "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/"
                        "tesseract-ocr-w64-setup-5.5.0.20241111.exe"
                    ),
                    filename="tesseract-ocr-w64-setup-5.5.0.20241111.exe",
                    expected_size=21_381_872,
                    sha256="F3FC4236425B690C8BE756F35793F77394EE004BE0A6460A440C754D892F68BC",
                    target_subdir="downloads",
                ),
                RuntimeDownload(
                    download_id="tessdata-eng",
                    url=f"{tessdata_base}/eng.traineddata",
                    filename="eng.traineddata",
                    expected_size=4_113_088,
                    sha256="7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2",
                    target_subdir="Tesseract-OCR/tessdata",
                ),
                RuntimeDownload(
                    download_id="tessdata-jpn",
                    url=f"{tessdata_base}/jpn.traineddata",
                    filename="jpn.traineddata",
                    expected_size=2_471_260,
                    sha256="1F5DE9236D2E85F5FDF4B3C500F2D4926F8D9449F28F5394472D9E8D83B91B4D",
                    target_subdir="Tesseract-OCR/tessdata",
                ),
                RuntimeDownload(
                    download_id="tessdata-chi_sim",
                    url=f"{tessdata_base}/chi_sim.traineddata",
                    filename="chi_sim.traineddata",
                    expected_size=2_469_156,
                    sha256="A5FCB6F0DB1E1D6D8522F39DB4E848F05984669172E584E8D76B6B3141E1F730",
                    target_subdir="Tesseract-OCR/tessdata",
                ),
                RuntimeDownload(
                    download_id="tessdata-chi_tra",
                    url=f"{tessdata_base}/chi_tra.traineddata",
                    filename="chi_tra.traineddata",
                    expected_size=2_366_642,
                    sha256="529C5B5797D64B126065CD55F2BB4C7FD7B15790798091B1FF259941A829330B",
                    target_subdir="Tesseract-OCR/tessdata",
                ),
            ),
        )

    def validate_development_root(self, runtime_root: str | Path) -> Path:
        resolved = Path(runtime_root).resolve()
        if resolved.drive.upper() != "E:":
            raise ValueError(f"development runtime root must be on E drive: {resolved}")
        return resolved

    def validate_installed_root(self, runtime_root: str | Path) -> Path:
        return Path(runtime_root).resolve()

    def runtime_settings(
        self,
        runtime_root: str | Path,
        install_root: str | Path | None = None,
    ) -> dict[str, str]:
        runtime = Path(runtime_root).resolve()
        install = Path(install_root).resolve() if install_root is not None else None
        return {
            "runtime_root": self._portable_path(runtime, install),
            "tesseract_command": self._portable_path(
                runtime / "Tesseract-OCR" / "tesseract.exe",
                install,
            ),
            "ocr_language": "+".join(self.ocr_languages),
            "comet_command": self._portable_path(
                runtime / "comet-score.cmd",
                install,
            ),
            "comet_model": self.comet_model,
            "comet_model_storage_path": self._portable_path(
                runtime / "comet-models",
                install,
            ),
        }

    @staticmethod
    def _portable_path(path: Path, install_root: Path | None) -> str:
        if install_root is None:
            return str(path)
        try:
            relative = path.relative_to(install_root)
        except ValueError:
            return str(path)
        return relative.as_posix()
