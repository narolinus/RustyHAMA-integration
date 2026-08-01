# RustyHAMA Integration

RustyHAMA connects Android wall tablets from API 17 as native devices to Home Assistant 2026.7 or newer. The integration is the central source for dashboards, profiles, device settings, provider connections and commands. A tablet receives neither a general Home Assistant user token nor a provider key.

Each paired tablet is registered as its own config subentry and HA device. The device's HA area is also the room context for its Assist satellite. The integration provides an Assist satellite, optional cameras and media player, plus sensor, binary sensor, switch, number, select and button entities.

## Guiding principles

| Principle | Implementation |
|---|---|
| Secure pairing | HTTPS, short-lived one-time code or QR token, revocable device credential |
| Central configuration | Profiles plus a device-specific RFC 7396 merge patch |
| Atomic activation | Draft, validation, publish, device ACK and last valid revision |
| Least privilege | Only required states and typed, server-approved operations |
| Equal documentation | German, English and French with the same page structure |

## Getting started

Start with [Installation and pairing](installation-pairing.md). [Configuration and editor](configuration-editor.md) describes dashboards. For failures, use [Operations and troubleshooting](operations.md) and the integration diagnostics.

!!! warning
    The 0.1 architecture does not migrate old `/local/*.json` files, user tokens, webhooks or global events. HTTP and blanket certificate-error bypasses are unsupported.
