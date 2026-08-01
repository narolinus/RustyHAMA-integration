# Betrieb und Fehlersuche {#betrieb-und-fehlersuche}

## Normalbetrieb {#normalbetrieb}

Der Android-Foreground-Service startet standardmäßig nach dem Boot und hält Gerätekanal, Voice, Kamera und Medien aktiv. Die App arbeitet ohne HA mit der letzten bestätigten Konfiguration weiter; HA-abhängige Controls zeigen den nicht verfügbaren Zustand. In HA vergleichen `config_revision` und `acknowledged_revision` Soll und bestätigten Stand.

## Diagnosefolge {#diagnosefolge}

1. Prüfe Online/Last Seen und Dienststatus am HA-Gerät.
2. Vergleiche Konfigurationsrevision und Geräte-ACK.
3. Prüfe HTTPS-URL, DNS, Zertifikatslaufzeit und gepinnten Fingerprint.
4. Öffne die redigierte Diagnose der Integration; Provider-Keys und Credential-Hashes dürfen dort nicht erscheinen.
5. Prüfe bei Voice Mikrofonberechtigung, Pipeline, STT/TTS und VAD.
6. Prüfe bei Kamera Facing, gewählte Auflösung, FPS, LAN-Erreichbarkeit und Transportmodus.

## Häufige Fehler {#haufige-fehler}

| Symptom | Ursache und Maßnahme |
|---|---|
| Pairing-Code abgelehnt | Code abgelaufen, verbraucht oder Fehlversuchslimit erreicht; neuen Code erzeugen |
| Fingerprint geändert | Verbindung nicht bestätigen; Zertifikat und möglichen Proxy/DNS-Angriff prüfen |
| Revision bleibt unbestätigt | App hat Schema oder Referenz abgelehnt; Geräte- und HA-Log prüfen, letzte gültige Revision bleibt aktiv |
| Widgets nicht verfügbar | Gerät offline oder Entity vorübergehend nicht in HA vorhanden |
| Assist bleibt bei Listening | Audioformat, Streamende, VAD und STT-Pipeline prüfen |
| Kamera lädt nicht | direkten HTTPS-Pfad prüfen oder Tunneltransport wählen |

## Widerruf und Wiederherstellung {#widerruf-und-wiederherstellung}

Entferne ein verlorenes Gerät im Panel; dadurch werden Session, Credential, Subentry und HA-Gerät widerrufen. Nach einer Neuinstallation der App ist wegen deaktiviertem Backup ein neues Pairing erforderlich. Ein Rollback der Konfiguration erzeugt stets eine neue Revision und verändert keine frühere Historie.
