#!/usr/bin/env python3
"""Add deterministic, Zensical-safe ASCII anchors to Markdown headings."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+\{#[^}]+\})?\s*$")
MARKUP = re.compile(r"[`*_~\[\]()]|<[^>]+>")


def slug(value: str) -> str:
    value = value.replace("ß", "ss").replace("ẞ", "ss")
    value = value.replace("Æ", "Ae").replace("æ", "ae")
    value = value.replace("Œ", "Oe").replace("œ", "oe")
    value = unicodedata.normalize("NFKD", MARKUP.sub(" ", value))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value or not value[0].isalpha():
        value = f"section-{value}".rstrip("-")
    return value


for language in ("de", "en", "fr"):
    for path in (ROOT / "docs" / language).rglob("*.md"):
        result: list[str] = []
        used: set[str] = set()
        in_fence = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                result.append(line)
                continue
            match = None if in_fence else HEADING.fullmatch(line)
            if match is None:
                result.append(line)
                continue
            prefix, title = match.groups()
            anchor = slug(title)
            candidate = anchor
            suffix = 2
            while candidate in used:
                candidate = f"{anchor}-{suffix}"
                suffix += 1
            used.add(candidate)
            result.append(f"{prefix} {title} {{#{candidate}}}")
        path.write_text("\n".join(result) + "\n", encoding="utf-8")
