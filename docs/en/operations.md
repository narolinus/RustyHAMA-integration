# Operations and troubleshooting

## Normal operation

The Android foreground service starts after boot by default and keeps the device channel, voice, camera and media active. Without HA, the app continues with its last acknowledged configuration; HA-dependent controls show unavailable. In HA, `config_revision` and `acknowledged_revision` compare desired and confirmed state.

## Diagnostic sequence

1. Check online/last seen and service status on the HA device.
2. Compare configuration revision and device acknowledgement.
3. Check HTTPS URL, DNS, certificate validity and pinned fingerprint.
4. Open redacted integration diagnostics; provider keys and credential hashes must be absent.
5. For voice, check microphone permission, pipeline, STT/TTS and VAD.
6. For camera, check facing, selected resolution, FPS, LAN reachability and transport.

## Common failures

| Symptom | Cause and action |
|---|---|
| Pairing code rejected | expired, consumed or attempt limit reached; create a new code |
| Fingerprint changed | do not confirm; inspect certificate and possible proxy/DNS attack |
| Revision stays unacknowledged | app rejected schema or reference; inspect logs; last valid revision remains active |
| Widgets unavailable | device offline or entity temporarily absent in HA |
| Assist remains listening | check audio format, stream end, VAD and STT pipeline |
| Camera does not load | verify direct HTTPS route or select tunnel transport |

## Revocation and recovery

Remove a lost device in the panel; this revokes its session, credential, subentry and HA device. Reinstalling the app requires new pairing because backup is disabled. A configuration rollback always creates a new revision and never changes earlier history.
