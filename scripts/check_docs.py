#!/usr/bin/env python3
"""Enforce equal DE/EN/FR documentation structure and field coverage."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LANGUAGES = ("de", "en", "fr")
FORBIDDEN = re.compile(r"\b(?:TODO|TBD|FIXME|STUB|FALLBACK)\b", re.IGNORECASE)
CODE_FIELD = re.compile(r'"([a-z][a-z0-9_.-]+)"\s*:')
LINK = re.compile(r"\[[^]]+\]\((?!https?://|#)([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+.+?\s+\{#([^}]+)\}\s*$")
ANCHOR = re.compile(r"^[a-z][a-z0-9-]*$")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


manifest = json.loads((DOCS / "page-manifest.json").read_text(encoding="utf-8"))
pages: list[str] = manifest["pages"]
for language in LANGUAGES:
    actual = sorted(
        str(path.relative_to(DOCS / language))
        for path in (DOCS / language).rglob("*.md")
    )
    if actual != sorted(pages):
        fail(f"{language}: page manifest mismatch: {actual}")
    for path in (DOCS / language).rglob("*.md"):
        anchors: set[str] = set()
        in_fence = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or not line.startswith("#"):
                continue
            match = HEADING.fullmatch(line)
            if not match:
                fail(f"{language}/{path.relative_to(DOCS / language)}:{number}: missing explicit ASCII anchor")
            anchor = match.group(2)
            if not ANCHOR.fullmatch(anchor):
                fail(f"{language}/{path.relative_to(DOCS / language)}:{number}: invalid anchor {anchor}")
            if anchor in anchors:
                fail(f"{language}/{path.relative_to(DOCS / language)}:{number}: duplicate anchor {anchor}")
            anchors.add(anchor)

for page in pages:
    texts = {
        language: (DOCS / language / page).read_text(encoding="utf-8")
        for language in LANGUAGES
    }
    for language, text in texts.items():
        if FORBIDDEN.search(text):
            fail(f"{language}/{page}: unfinished marker")
        for target in LINK.findall(text):
            path = (DOCS / language / target.split("#", 1)[0]).resolve()
            if target and not path.exists():
                fail(f"{language}/{page}: broken link {target}")
    headings = {
        language: [line.count("#", 0, len(line) - len(line.lstrip("#")))
                   for line in text.splitlines() if line.startswith("#")]
        for language, text in texts.items()
    }
    if len({tuple(value) for value in headings.values()}) != 1:
        fail(f"{page}: heading structure differs: {headings}")
    fields = {language: set(CODE_FIELD.findall(text)) for language, text in texts.items()}
    if len({frozenset(value) for value in fields.values()}) != 1:
        fail(f"{page}: JSON field coverage differs: {fields}")

print(f"Documentation parity OK: {len(pages)} pages x {len(LANGUAGES)} languages")
