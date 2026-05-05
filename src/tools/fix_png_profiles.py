from argparse import ArgumentParser
from pathlib import Path

from PIL import Image


def normalize_png_profile(path: Path) -> bool:
    with Image.open(path) as image:
        rewritten = image.copy()

    rewritten.info.pop("icc_profile", None)
    rewritten.save(path, format="PNG", optimize=True)
    return True


def scan_and_fix(root: Path) -> list[Path]:
    fixed: list[Path] = []
    for path in root.rglob("*.png"):
        if normalize_png_profile(path):
            fixed.append(path)
    return fixed


def main() -> int:
    parser = ArgumentParser(description="Normalize PNG profiles to avoid iCCP warnings")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    args = parser.parse_args()

    fixed = scan_and_fix(Path(args.root))
    print(f"fixed_png_count={len(fixed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
