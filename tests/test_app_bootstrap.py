from pathlib import Path
import subprocess
import sys


def test_app_imports_without_manual_src_path_injection():
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-c", "import app; print('ok')"]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
