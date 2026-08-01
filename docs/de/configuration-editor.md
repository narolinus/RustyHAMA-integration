# Konfiguration und Editor {#konfiguration-und-editor}

## Profile, Overrides und effektive Konfiguration {#profile-overrides-und-effektive-konfiguration}

Ein Profil enthält ein vollständiges Dashboard. Ein Gerät referenziert genau ein Profil und kann einen Override speichern. Dieser folgt RFC 7396: Objekte werden rekursiv zusammengeführt, Arrays vollständig ersetzt und `null` entfernt einen Schlüssel. Provider-Bindings werden getrennt gespeichert und nie zu Secrets aufgelöst.

```json
{
  "schema_version": 1,
  "theme": "dark",
  "tabs": [
    {
      "id": "overview",
      "title": "Übersicht",
      "columns": 2,
      "widgets": [{"id": "clock", "type": "clock"}]
    }
  ]
}
```

## JSON- und visueller Editor {#json-und-visueller-editor}

JSON ist immer die Standardansicht. Der Code-Editor bietet Syntaxhervorhebung, Zeilennummern, Tab-Einrückung und direkte Syntaxprüfung. Getrennte Ansichten zeigen Profilentwurf, Geräte-Override und schreibgeschützte effektive Konfiguration. Speichern erzeugt beim Profil einen Entwurf; erst **Veröffentlichen** validiert Referenzen, erzeugt eine monotone Revision und verteilt sie. Das Speichern eines Geräte-Overrides veröffentlicht und verteilt den Merge-Patch sofort. Fehlende Provider blockieren die Veröffentlichung. Vorübergehend fehlende HA-Entities werden als Warnung behandelt.

Der visuelle Editor bearbeitet vollständige Profile. Er zeigt die realen Theme-Felder für Farben, Radius, Skalierung, Padding und Gap sowie Tabs, Rasterpositionen, Spans und die üblichen nativen Widgettypen. Widgets können angelegt, sortiert und gelöscht werden. Nicht dargestellte oder komplexe Felder bleiben unverändert erhalten. Geräte-Overrides sind RFC-7396-Merge-Patches und werden deshalb im JSON-Editor bearbeitet; ihre zusammengeführte Wirkung ist rechts sichtbar.

## Vorschau {#vorschau}

Wähle ein Gerät, um dessen zuletzt gemeldete physische und nutzbare Pixelmaße, Activity-Innenfläche, Orientierung, Dichte, Density-DPI, Font-Scale und bekannte Insets zu verwenden. Die Vorschau rechnet dp und sp mit diesen Werten um und skaliert das Ergebnis proportional in den Browserbereich. Portrait und Landscape können kontrolliert umgeschaltet werden. Offline werden die letzten Gerätewerte verwendet; das generische Tablet ist ausdrücklich nicht gerätespezifisch.

Die Vorschau verwendet aktuelle HA-States, die echte Widgetfamilie, Tab-Reihenfolge, explizite Zeilen/Spalten, Spans, Zellhöhen und Theme-Werte. `auto_entities` wird über denselben serverseitigen Compiler wie beim Verteilen an Android aufgelöst. Wegen unterschiedlicher Android- und Browser-Schrift- und Medien-Engines bleibt sie dennoch eine Annäherung. Maßgeblich ist das native Gerät. Die Kopfzeile verlinkt direkt auf die vollständige Widget-Dokumentation mit allen JSON-Codes.

## Revisionen und Rollback {#revisionen-und-rollback}

Es werden zwanzig unveränderliche Revisionen aufbewahrt. Ein Rollback überschreibt keine Historie, sondern veröffentlicht den gewählten Stand als neue höhere Revision. Lehnt die App eine Konfiguration ab, bleibt die letzte gültige Konfiguration aktiv und HA zeigt die nicht bestätigte Revision.
