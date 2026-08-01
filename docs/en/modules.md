# Feature modules

## Voice

The Assist satellite supports `IDLE`, `LISTENING`, `PROCESSING` and `RESPONDING`, server wake-word detection, push-to-talk, pipeline and VAD selection, TTS, announcements, and started or continued conversations. Android streams 16 kHz mono PCM through a short-lived authenticated stream. Pipeline events and TTS media return on the control channel. Local wake-word inference remains a future capability and is not part of 0.1.

## Camera

The app reports available cameras. The setup assistant configures facing, resolution, maximum width, FPS, JPEG quality and transport. In the default direct mode, HA loads snapshots or MJPEG over pinned device HTTPS in the LAN. Tunnel mode carries frames over short-lived authenticated streams. `camera.*` proxies content through HA; device addresses and access data are not published.

## Media player and sensors

The optional Android media player supports URL/TTS, play/pause/stop, seek, volume, mute, position, metadata and cover art. It is disabled by default and may then be imported by Music Assistant. Minimum intervals and change thresholds limit network and Recorder load. Location is neither requested nor transmitted.

## Providers

Multiple named Immich and Music Assistant connections are supported. Provider secrets remain only in private HA storage, are redacted from diagnostics and never sent to Android. Immich search and media retrieval run server-side. Music Assistant primarily uses its official HA integration, entities and actions; only missing existing behavior belongs in a narrow server adapter.

## Dashboard parity

Themes, tabs, badges, conditions, nested grids, graphs, calendar mutations, media groups, screensaver, Immich views, Music Assistant tab, voice button, HA state control and every documented app widget family and alias remain supported.
