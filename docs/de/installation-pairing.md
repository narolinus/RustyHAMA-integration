# Installation und Pairing {#installation-und-pairing}

## Voraussetzungen {#voraussetzungen}

- Home Assistant Core 2026.7 oder neuer
- ein von Tablet und Browser erreichbarer HTTPS-Endpunkt
- RustyHAMA-App 0.1 oder neuer
- Admin-Rechte für Einrichtung und Panel

## HACS-Installation {#hacs-installation}

Öffne HACS, füge [`narolinus/RustyHAMA-integration`](https://github.com/narolinus/RustyHAMA-integration) als benutzerdefiniertes Repository vom Typ „Integration“ hinzu, installiere RustyHAMA und starte Home Assistant neu. Lege anschließend unter **Einstellungen → Geräte & Dienste** die Integration **RustyHAMA** an. Sie existiert genau einmal; Geräte werden im Seitenleisten-Panel hinzugefügt.

## Gerät vorbereiten {#gerat-vorbereiten}

Öffne **RustyHAMA → Geräte**, gib Name, Profil und optional die HA-Bereichs-ID an und erzeuge die Kopplung. Der achtstellige Code ist zehn Minuten gültig und kann höchstens fünfmal falsch eingegeben werden. Der QR-Code enthält HA-URL und ein hochentropisches Einmaltoken; ein vorhandener Zertifikats-Fingerprint wird ebenfalls übernommen.

Gib in der App URL und Code ein oder scanne den QR-Code. Nach erfolgreicher Kopplung speichert Android das zufällige 256-Bit-Credential im privaten, vom Backup ausgeschlossenen App-Speicher. Home Assistant speichert ausschließlich dessen Hash.

## Zertifikate {#zertifikate}

Öffentlich vertrauenswürdige Zertifikate werden mit Conscrypt und dem im Release gepflegten CA-Satz geprüft. Bei einem selbstsignierten oder auf dem alten Gerät unbekannten Zertifikat zeigt die App den SHA-256-Fingerprint. Vergleiche ihn über einen zweiten vertrauenswürdigen Weg mit Home Assistant, bevor du **Vertrauen und pinnen** wählst.

!!! danger
    Bestätige nie einen unerwartet geänderten Fingerprint. Widerrufe das Gerät im Panel, prüfe HA-Zertifikat und DNS und kopple erst danach neu.

## Nach der Kopplung {#nach-der-kopplung}

Das HA-Gerät zeigt seinen Onlinezustand, die Konfigurationsrevision und Displaydaten. Weise einen Bereich zu, falls dies beim Anlegen nicht geschah. Aktiviere den standardmäßig deaktivierten MediaPlayer oder Hardware-Sensoren nur bei Bedarf. Ein Credential kann im Panel rotiert werden; ein entferntes Gerät verliert sofort seine Verbindung.
