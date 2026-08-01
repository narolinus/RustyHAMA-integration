# Protocol and security {#protocol-and-security}

## Endpoints {#endpoints}

| Endpoint | Function |
|---|---|
| `POST /api/rustyhama/v1/pair` | one-time pairing without an HA user token |
| `/api/rustyhama/v1/device/ws` | persistent control channel |
| `/api/rustyhama/v1/device/streams/{session_id}` | voice, camera and media streams |

Every message carries protocol version, ID, type, timestamp, revision and payload. Message IDs support acknowledgements, deduplication and timeouts. A new session generation unambiguously replaces an old connection.

## Connection behavior {#connection-behavior}

Heartbeats detect half-open WebSockets. Reconnect uses exponential delay with jitter. Bounded queues and separate stream channels protect the control channel from backpressure. Notifications and actions are discarded while offline and never played late. Only desired state and the newest configuration converge after reconnect.

## Permission boundary {#permission-boundary}

The device credential authenticates exactly one device. It is random, revocable and rotatable; HA stores only SHA-256. Devices cannot send free-form service calls. Entity and operation must appear in the effective dashboard or server allowlist. Provider secrets are recursively redacted before logging and diagnostics.

## TLS and host protection {#tls-and-host-protection}

Device communication accepts HTTPS/WSS only. Public certificates are validated normally. Unknown certificates require manual fingerprint confirmation and are pinned afterwards; a certificate change breaks the connection. Android app backup is disabled. Encryption of HA disks and backups remains the host's responsibility.

!!! note
    The protocol becomes jointly stable at `1.0.0`. Earlier releases still negotiate versions strictly; unknown versions and invalid payloads are rejected.
