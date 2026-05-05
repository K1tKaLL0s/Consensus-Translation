from pathlib import Path

from PIL import Image

from src.tools.fix_png_profiles import normalize_png_profile, scan_and_fix


def test_normalize_png_profile_rewrites_file(tmp_path: Path) -> None:
    path = tmp_path / "bad.png"
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(path)

    changed = normalize_png_profile(path)

    assert changed is True
    assert path.exists()


def test_scan_and_fix_finds_pngs(tmp_path: Path) -> None:
    Image.new("RGB", (2, 2), color=(0, 255, 0)).save(tmp_path / "a.png")
    Image.new("RGB", (2, 2), color=(0, 0, 255)).save(tmp_path / "b.png")

    fixed = scan_and_fix(tmp_path)

    assert len(fixed) == 2
