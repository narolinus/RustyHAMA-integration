# Protokoll und Sicherheit

## Endpunkte

| Endpunkt | Funktion |
|---|---|
| `POST /api/rustyhama/v1/pair` | Einmalige Kopplung ohne HA-Benutzertoken |
| `/api/rustyhama/v1/device/ws` | dauerhafter Kontrollkanal |
| `/api/rustyhama/v1/device/streams/{session_id}` | Voice-, Kamera- und Medienstreams |

Jede Nachricht enthält Protokollversion, ID, Typ, Zeitstempel, Revision und Payload. Nachrichten-IDs dienen ACK, Deduplizierung und Timeout. Eine neue Session-Generation ersetzt eine alte Verbindung eindeutig.

## Verbindungsverhalten

Heartbeats erkennen halb offene WebSockets. Reconnect verwendet exponentielle Verzögerung mit Jitter. Begrenzte Queues und getrennte Streamkanäle schützen den Kontrollkanal vor Backpressure. Benachrichtigungen und Aktionen werden offline verworfen und nicht verspätet abgespielt. Nur gewünschter Zustand und neueste Konfiguration konvergieren nach Reconnect.

## Berechtigungsgrenze

Das Geräte-Credential authentifiziert exakt ein Device. Es ist zufällig, widerrufbar und rotierbar; HA speichert nur SHA-256. Geräte dürfen keine freien Serviceaufrufe senden. Entity und Operation müssen im effektiven Dashboard beziehungsweise in der serverseitigen Allowlist liegen. Provider-Secrets werden vor Logs und Diagnosen rekursiv redigiert.

## TLS und Hostschutz

Gerätekommunikation akzeptiert ausschließlich HTTPS/WSS. Öffentliche Zertifikate werden normal validiert. Unbekannte Zertifikate erfordern eine manuelle Fingerprint-Bestätigung und werden danach gepinnt; ein Zertifikatswechsel bricht die Verbindung. Das lokale Android-Backup ist deaktiviert. Verschlüsselung von HA-Datenträgern und HA-Backups bleibt Aufgabe des Hosts.

!!! note
    Das Protokoll ist ab `1.0.0` gemeinsam stabil. Vorher wird die Version trotzdem strikt ausgehandelt; unbekannte Versionen und ungültige Payloads werden abgewiesen.
