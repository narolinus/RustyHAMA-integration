# Entwicklung und Releases

## Repository und Tests

Die Integration liegt unter `custom_components/rustyhama`. Sprachneutrale Schemas stehen in `schemas`, gemeinsame Python-/Java-Testvektoren in `test-vectors`. Push-CI führt pytest, Ruff, MyPy, Frontend- und Viewport-Snapshot-Tests, Hassfest, HACS-Validation, Dokumentparität und drei strikte Zensical-Builds aus.

Lokale Kernprüfung:

```bash
python -m pytest
ruff check .
mypy custom_components/rustyhama
python scripts/check_docs.py
zensical build --clean --strict
zensical build --config-file zensical.en.toml --clean --strict
zensical build --config-file zensical.fr.toml --clean --strict
```

## Versionsvertrag

App und Integration beginnen bei `0.1.0`. `1.0.0` bezeichnet den ersten gemeinsam stabilen Protokollstand. Ein Release-Tag muss exakt der Version in `manifest.json` entsprechen. Forgejo ist führend, veröffentlicht die dreisprachige Dokumentation unter `daniel.snii.de/RustyHAMA-Integration/` und spiegelt Commit und Tag nach GitHub.

GitHub erzeugt `rustyhama.zip` mit dem vollständigen Verzeichnis `custom_components/rustyhama`. HACS installiert ausschließlich vollständige GitHub-Releases. Ein Release-Gate testet Installation, Update, Versionsgleichheit und reproduzierbaren ZIP-Inhalt.

## Fertig-Definition

Eine Funktion ist erst fertig, wenn Python-, Frontend- und Android-Vertragstests vorliegen, Fehlerfälle geprüft sind und alle zugehörigen Erklärungen, Beispiele, Tabellen und Warnungen vollständig in Deutsch, Englisch und Französisch enthalten sind. Das Seitenmanifest, identische Überschriftenstruktur, interne Links und JSON-Feldabdeckung werden maschinell geprüft.
