# Funktionsmodule

## Voice

Der Assist Satellite unterstützt `IDLE`, `LISTENING`, `PROCESSING` und `RESPONDING`, serverseitige Wakeword-Erkennung, Push-to-talk, Pipeline- und VAD-Auswahl, TTS, Ansagen sowie gestartete und fortgesetzte Gespräche. Android streamt 16-kHz-Mono-PCM über einen kurzlebigen authentifizierten Stream. Pipeline-Ereignisse und TTS-Medien laufen über den Kontrollkanal zurück. Lokale Wakeword-Inferenz ist für eine spätere Capability vorgesehen, aber nicht Teil von 0.1.

## Kamera

Die App meldet verfügbare Kameras. Der Assistent konfiguriert Facing, Auflösung, maximale Breite, FPS, JPEG-Qualität und Transport. Im direkten Standardmodus lädt HA Snapshot oder MJPEG über die gepinnte Geräte-HTTPS-Verbindung im LAN. Der Tunnelmodus transportiert Frames über kurzlebige authentifizierte Streams. `camera.*` proxyet Inhalte über HA; Geräteadresse und Zugangsdaten werden nicht öffentlich ausgegeben.

## MediaPlayer und Sensoren

Der optionale Android-MediaPlayer unterstützt URL/TTS, Play/Pause/Stop, Seek, Lautstärke, Mute, Position, Metadaten und Cover. Er ist standardmäßig deaktiviert und kann danach von Music Assistant importiert werden. Sensorintervalle und Änderungsschwellen begrenzen Netzwerk- und Recorderlast. Standort wird weder angefordert noch übertragen.

## Provider

Mehrere benannte Immich- und Music-Assistant-Verbindungen sind möglich. Provider-Secrets liegen ausschließlich im privaten HA-Storage, werden in Diagnoseausgaben redigiert und niemals an Android gesendet. Immich-Suche und Medienabruf erfolgen serverseitig. Music Assistant nutzt primär dessen offizielle HA-Integration, Entities und Actions; nur fehlende Bestandsfunktionen gehören in einen eng begrenzten Serveradapter.

## Dashboard-Parität

Unterstützt bleiben Themes, Tabs, Badges, Bedingungen, verschachtelte Grids, Graphen, Kalenderänderungen, Mediengruppen, Screensaver, Immich-Ansichten, Music-Assistant-Tab, Voice-Button und HA-State-Steuerung sowie alle dokumentierten Widgetfamilien und Aliase der App.
