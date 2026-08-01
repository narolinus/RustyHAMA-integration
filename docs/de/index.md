# RustyHAMA-Integration

RustyHAMA verbindet Android-Wandtablets ab API 17 als native Geräte mit Home Assistant 2026.7 oder neuer. Die Integration ist die zentrale Quelle für Dashboards, Profile, Geräteeinstellungen, Provider-Zugänge und Befehle. Ein Tablet erhält kein allgemeines Home-Assistant-Benutzertoken und niemals einen Provider-Key.

Jedes gekoppelte Tablet wird als eigene Config-Subentry und als HA-Gerät registriert. Der am Gerät gewählte HA-Bereich ist zugleich der Raumkontext des Assist Satellite. Die Integration stellt Assist Satellite, optionale Kameras und MediaPlayer sowie Sensor-, Binary-Sensor-, Switch-, Number-, Select- und Button-Entities bereit.

## Leitprinzipien

| Prinzip | Umsetzung |
|---|---|
| Sichere Kopplung | HTTPS, kurzlebiger Einmalcode oder QR-Token, widerrufbares Geräte-Credential |
| Zentrale Konfiguration | Profile plus gerätespezifischer RFC-7396-Merge-Patch |
| Atomare Aktivierung | Entwurf, Validierung, Veröffentlichung, Geräte-ACK und letzte gültige Revision |
| Geringe Rechte | Nur benötigte States und typisierte, serverseitig erlaubte Operationen |
| Gleichwertige Doku | Deutsch, Englisch und Französisch mit identischer Seitenstruktur |

## Einstieg

Beginne mit [Installation und Pairing](installation-pairing.md). Die Konfiguration wird unter [Konfiguration und Editor](configuration-editor.md) erklärt. Für einen Fehlerfall helfen [Betrieb und Fehlersuche](operations.md) und die Diagnoseausgabe der Integration.

!!! warning
    Die 0.1-Architektur migriert keine alten `/local/*.json`-Dateien, Benutzer-Tokens, Webhooks oder globalen Events. HTTP und pauschales Ignorieren von Zertifikatsfehlern werden nicht unterstützt.
