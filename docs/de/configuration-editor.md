# Konfiguration und Editor

## Profile, Overrides und effektive Konfiguration

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

## JSON- und visueller Editor

JSON ist immer die Standardansicht. Der Editor bietet getrennte Ansichten für Profilentwurf, Geräte-Override und schreibgeschützte effektive Konfiguration. Speichern erzeugt einen Entwurf; erst **Veröffentlichen** validiert Referenzen, erzeugt eine monotone Revision und verteilt sie. Fehlende Provider blockieren die Veröffentlichung. Vorübergehend fehlende HA-Entities werden als Warnung behandelt.

Der visuelle Editor bearbeitet Theme, Tabs, Spalten und übliche native Widgets. Unbekannte oder komplexe Blöcke bleiben unverändert erhalten. Dadurch kann jederzeit ohne Datenverlust zum JSON-Editor gewechselt werden.

## Vorschau

Wähle ein Gerät, um dessen zuletzt gemeldete physische und nutzbare Pixelmaße, Activity-Innenfläche, Orientierung, Dichte, Density-DPI, Font-Scale und bekannte Insets zu verwenden. Die Vorschau rechnet dp und sp mit diesen Werten um und skaliert das Ergebnis proportional in den Browserbereich. Portrait und Landscape können kontrolliert umgeschaltet werden. Offline werden die letzten Gerätewerte verwendet; das generische Tablet ist ausdrücklich nicht gerätespezifisch.

Die Vorschau verwendet aktuelle HA-States, bleibt wegen unterschiedlicher Android- und Browser-Schrift-Engines aber eine Annäherung. Maßgeblich ist das native Gerät.

## Revisionen und Rollback

Es werden zwanzig unveränderliche Revisionen aufbewahrt. Ein Rollback überschreibt keine Historie, sondern veröffentlicht den gewählten Stand als neue höhere Revision. Lehnt die App eine Konfiguration ab, bleibt die letzte gültige Konfiguration aktiv und HA zeigt die nicht bestätigte Revision.
