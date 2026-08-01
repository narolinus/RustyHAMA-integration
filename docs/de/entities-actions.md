# Entities und Actions

## Geräte-Entities

Jedes Gerät besitzt ein echtes `assist_satellite.*`. Für aktivierte Kameras entstehen `camera.*`; `media_player.*` ist vorhanden, aber standardmäßig deaktiviert. Laufzeitnahe Einstellungen tragen `EntityCategory.CONFIG`, Diagnosewerte `EntityCategory.DIAGNOSTIC`.

Standardmäßig aktive Sensoren umfassen Batterie, Laden, Stromquelle, WLAN-Signal, Netzwerk und IP, aktiven Tab, Online/Last Seen, App-/Android-Version, Uptime, Speicher, Displaygeometrie sowie Screensaver-, Voice-, Kamera- und Dienststatus. Licht, Nähe, Beschleunigung, Gyroskop, Magnetfeld, Druck, Feuchte, Temperatur, Rotation und Schritte werden bei vorhandener Hardware angelegt, bleiben aber deaktiviert.

Switches, Numbers und Selects steuern unter anderem Profil, Helligkeit, Bildschirmbetrieb, Voice/Wakeword, VAD, Audioweg, Screensaver, Kamera-FPS/Qualität/Auflösung/Transport, MediaPlayer und Sensorintervall. Buttons laden die Konfiguration neu, wecken den Bildschirm oder starten den Dienst neu.

## Eigene Actions

| Action | Zweck |
|---|---|
| `rustyhama.send_notification` | Overlay bei sichtbarer App, sonst Android-Systembenachrichtigung |
| `rustyhama.set_active_tab` | Tab anhand Index oder stabiler ID wählen |
| `rustyhama.set_screensaver` | Screensaver ein-, aus- oder umschalten |
| `rustyhama.reload_configuration` | neueste veröffentlichte Konfiguration senden |

```yaml
action: rustyhama.send_notification
data:
  device_id: 0123456789abcdef
  title: Haustür
  message: Es hat geklingelt.
  play_sound: true
```

Voice-Ansagen und Gespräche verwenden die Standard-Actions von `assist_satellite`; Wiedergabe verwendet `media_player`. Widgets dürfen keine beliebigen HA-Dienste aufrufen. Die Integration extrahiert die im effektiven Dashboard referenzierten Entities, überträgt nur deren States und erlaubt pro Domain eine feste Menge typisierter Operationen.
