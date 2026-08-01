#!/usr/bin/env python3
"""Copy the single shared documentation asset tree into all built editions."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "assets"

for destination in (ROOT / "site", ROOT / "site" / "en", ROOT / "site" / "fr"):
    if not destination.is_dir():
        raise SystemExit(f"Missing documentation build directory: {destination}")
    shutil.copytree(SOURCE, destination / "assets", dirs_exist_ok=True)

print("Shared documentation assets copied to DE, EN and FR builds")
