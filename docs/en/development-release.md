# Development and releases

## Repository and tests

The integration lives in `custom_components/rustyhama`. Language-neutral schemas are in `schemas`; shared Python/Java vectors are in `test-vectors`. Push CI runs pytest, Ruff, MyPy, frontend and viewport snapshots, Hassfest, HACS validation, documentation parity and three strict Zensical builds.

Local core checks:

```bash
python -m pytest
ruff check .
mypy custom_components/rustyhama
python scripts/check_docs.py
zensical build --clean --strict
zensical build --config-file zensical.en.toml --clean --strict
zensical build --config-file zensical.fr.toml --clean --strict
```

## Version contract

App and integration start at `0.1.0`. `1.0.0` marks the first jointly stable protocol. A release tag must exactly match `manifest.json`. Forgejo is authoritative, publishes all three documentation languages at `daniel.snii.de/RustyHAMA-Integration/`, and mirrors commit and tag to GitHub.

GitHub creates `rustyhama.zip` containing the complete `custom_components/rustyhama` directory. HACS installs complete GitHub releases only. A release gate tests installation, update, version equality and reproducible ZIP contents.

## Definition of done

A feature is complete only when Python, frontend and Android contract tests cover it, failure paths are exercised, and all associated explanations, examples, tables and warnings are complete in German, English and French. The page manifest, identical heading structure, internal links and JSON-field coverage are checked automatically.
