from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_render_guard() -> None:
    project_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        ["node", "--test", "tests/test_render_guard.mjs"],
        cwd=project_root,
        check=True,
    )
