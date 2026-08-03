# RustyHAMA Home Assistant integration instructions

## Project and repository authority

- This repository is a Python and Home Assistant project; Android API, Gradle and APK instructions from the parent workspace do not apply here.
- Integration repository: `/Users/daniel/Projekte/Android/RustyHAMA-Integration`
- Corresponding Android application: `/Users/daniel/Projekte/Android/RustyHA`
- Forgejo `daniel/RustyHAMA-Integration` is the leading repository.
- GitHub `narolinus/RustyHAMA-integration` is the public HACS mirror and not an independent development branch.
- Before relying on local versions or tags, fetch the leading Forgejo remote and inspect the actual remote state. Do not overwrite local user changes while synchronizing.
- Mirror only by fast-forward or when GitHub already contains the tagged commit; never overwrite divergent history.

## Home Assistant and HACS

- Integration domain: `rustyhama`.
- Current minimum target is Home Assistant 2026.7.
- Distribution currently supports installation as a HACS custom repository; official inclusion in the default HACS repository is not required.
- HACS release archives are named `rustyhama.zip` and contain the contents of `custom_components/rustyhama`.
- Keep HACS metadata, repository topics and brand assets under `custom_components/rustyhama/brand` valid.
- Full product documentation is maintained in the Android App repository. This repository keeps only concise README links to the app repository, published documentation and HACS installation instructions.
- Do not restore separate Zensical or multilingual documentation builds here.

## Versions and release flow

- The release tag without its `v` prefix, `custom_components/rustyhama/manifest.json` and `pyproject.toml` must contain the same version.
- Never infer the next version from conversation history or an unfetched checkout.
- Push the version commit to Forgejo and wait for green main-branch CI before creating the release tag.
- After tagging, verify the Forgejo mirror workflow, GitHub tag, GitHub release, `rustyhama.zip` and HACS detection/installation.
- Do not release the Android application merely to keep its version aligned with the integration.

## CI

- Forgejo CI is authoritative for implementation checks and uses the prebuilt toolchain on the `android_build` runner where configured.
- Select and run checks appropriate to the task and regression risk. Available project checks include Ruff, mypy, pytest, Node frontend tests, Hassfest and HACS archive validation.
- GitHub CI is limited to HACS-facing validation and release archive creation.
- Do not add repeated Python, Node, Zensical or Home Assistant toolchain installation when the Forgejo runner image already provides it.

## Architecture and configuration

- One main Config Entry manages the service; paired Android devices are represented by individual subentries and HA devices.
- HA areas provide device room context.
- The integration owns pairing, credential verification and revocation, device sessions, profiles, device overrides, `tab_order`, revisions, providers, dashboard compilation, typed commands, entities and diagnostics.
- Profiles contain complete dashboards. Device overrides follow RFC 7396: objects merge recursively, arrays replace inherited arrays, and `null` removes inherited values.
- `tab_order` explicitly reorders inherited tabs by their IDs.
- Compile expensive operations such as Auto-Entities filtering server-side and preserve unknown advanced blocks.
- The effective device configuration is secret-free, revisioned and compatible with the shared App schema.
- Configuration activation is acknowledged by the device. Failed activation retains the prior valid revision.
- Protocol, schema, pairing, dashboard, camera, Voice Assist and privacy changes require coordinated review against the Android repository.

## Session stability

- Maintain one current session generation per device and clean up replaced, half-open and disconnected sessions deterministically.
- Heartbeats must not be blocked by state forwarding, providers, Voice Assist, camera or media streams.
- Handle writes to closing WebSockets without unhandled tasks or repeated log errors.
- Use bounded queues, deduplication and backpressure for device traffic.
- Do not replay stale notifications or actions after reconnect; converge only desired state and the current configuration.
- Avoid blocking filesystem and network operations on Home Assistant's event loop.
- Redact device credentials, provider secrets and authorization data from logs and diagnostics.

## Dashboard editor and compiler

- The panel manages devices, profiles, device overrides, providers, revisions, pairing and dashboard editing.
- JSON is the default editor. The visual editor must preserve unknown advanced configuration.
- Preview geometry uses the selected device's viewport, density, font scale, insets and orientation, and must scale and center the complete device viewport.
- Pairing supports both manual codes and QR data.
- Link the central RustyHAMA documentation from the panel.
- Keep shared schemas, protocol messages and contract fixtures synchronized with the Android application.

## Camera

- Camera FPS are configured per device and the native MJPEG stream is proxied without snapshot-based throttling.
- Preserve the configured frame rate as far as the Android hardware and driver provide it.
- Validate every device camera URL against the paired device's current address, configured port, allowed base path, camera ID and known endpoint.
- Reject unexpected schemes, hosts, credentials, query strings and fragments.
- Do not expose device camera credentials or internal URLs through entity attributes.
- Direct LAN mode is standard and tunnel mode is an explicit fallback.

## Voice Assist and wakewords

- Implement a real `AssistSatelliteEntity` with pipeline selection, VAD, announcements, TTS and continued conversations.
- Server-side wakeword detection requires an independently configurable wakeword selection for every paired device.
- Expose the available server wakewords in HA, store the selected wakeword per device and apply it to that device's Assist pipeline/session.
- If the selected wakeword becomes unavailable, surface that state clearly instead of silently choosing another wakeword.
- Long utterances and Voice streams must reach HA's Assist pipeline without blocking control-channel heartbeats.

## Local privacy enforcement

- Camera and Voice Assist locks reported live by the Android device are authoritative; pairing capabilities are only an initial fallback.
- A locally locked feature is unavailable or off in HA and every attempt to activate it remotely is rejected.
- Expose the lock states as diagnostic entities.
- Never send a command or configuration that removes, resets or bypasses a local lock.
- Reconnect, profile changes and configuration publication must not imply that a local lock was cleared.

## Providers and local HA access

- Provider secrets stay in HA storage, are redacted and are never transferred to Android.
- Immich operations run server-side. Use official Music Assistant entities and actions where possible; custom adapters cover only missing functionality.
- Provider failures must not terminate the device session.
- When local HA access is needed, read `/Users/daniel/Projekte/Android/RustyHA/.agent-secrets/ha.env`.
- Never repeat credentials from that file in responses, logs, documentation, source files, commits, CI or published command output.
- Do not rotate credentials or create additional permanent HA users or tokens without explicit authorization.
