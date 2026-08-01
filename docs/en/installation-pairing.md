# Installation and pairing {#installation-and-pairing}

## Requirements {#requirements}

- Home Assistant Core 2026.7 or newer
- an HTTPS endpoint reachable by tablet and browser
- RustyHAMA app 0.1 or newer
- administrator rights for setup and panel

## HACS installation {#hacs-installation}

Open HACS, add [`narolinus/RustyHAMA-integration`](https://github.com/narolinus/RustyHAMA-integration) as a custom repository of type “Integration”, install RustyHAMA, and restart Home Assistant. Then add **RustyHAMA** under **Settings → Devices & services**. The service entry exists once; devices are added in its sidebar panel.

## Preparing a device {#preparing-a-device}

Open **RustyHAMA → Devices**, enter a name, profile and optional HA area ID, then create a pairing. The eight-digit code is valid for ten minutes and allows no more than five failed attempts. The QR code contains the HA URL and a high-entropy one-time token; an available certificate fingerprint is included too.

Enter URL and code in the app or scan the QR code. After pairing, Android stores the random 256-bit credential in private app storage excluded from backup. Home Assistant stores only its hash.

## Certificates {#certificates}

Publicly trusted certificates are verified with Conscrypt and the CA set maintained with the release. For a self-signed certificate, or one unknown to an old tablet, the app displays its SHA-256 fingerprint. Compare it with Home Assistant through a second trusted channel before choosing **Trust and pin**.

!!! danger
    Never confirm an unexpected fingerprint change. Revoke the device in the panel, inspect the HA certificate and DNS, and pair again only after resolving the cause.

## After pairing {#after-pairing}

The HA device shows online state, configuration revision and display details. Assign an area if none was selected initially. Enable the disabled-by-default media player or hardware sensors only when required. A credential can be rotated in the panel; removing a device immediately terminates its connection.
