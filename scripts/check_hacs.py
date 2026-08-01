#!/usr/bin/env python3
"""Validate the HACS metadata and release archive contract without GitHub API access."""

from __future__ import annotations

import json
import re
import struct
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "rustyhama"

hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))

assert hacs["content_in_root"] is False
assert hacs["zip_release"] is True
assert hacs["filename"] == "rustyhama.zip"
assert hacs["homeassistant"] == "2026.7.0"
assert manifest["domain"] == "rustyhama"
assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])

brand_sizes = {
    "icon.png": (256, 256),
    "icon@2x.png": (512, 512),
    "logo.png": (256, 256),
    "logo@2x.png": (512, 512),
}
for filename, expected_size in brand_sizes.items():
    image = (INTEGRATION / "brand" / filename).read_bytes()
    assert image[:8] == b"\x89PNG\r\n\x1a\n", filename
    assert struct.unpack(">II", image[16:24]) == expected_size, filename

with tempfile.TemporaryDirectory() as directory:
    archive = Path(directory) / hacs["filename"]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(INTEGRATION.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                output.write(path, path.relative_to(INTEGRATION))
    with zipfile.ZipFile(archive) as packaged:
        names = set(packaged.namelist())
        assert "manifest.json" in names
        assert "brand/icon.png" in names
        assert "brand/icon@2x.png" in names
        assert "brand/logo.png" in names
        assert "brand/logo@2x.png" in names
        assert "custom_components/rustyhama/manifest.json" not in names
        assert packaged.testzip() is None

print("HACS metadata and root-level release archive OK")
