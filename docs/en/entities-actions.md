# Entities and actions {#entities-and-actions}

## Device entities {#device-entities}

Every device has a real `assist_satellite.*`. Enabled cameras create `camera.*`; `media_player.*` exists but is disabled by default. Runtime settings use `EntityCategory.CONFIG`, diagnostics use `EntityCategory.DIAGNOSTIC`.

Enabled sensors cover battery, charging, power source, Wi-Fi signal, network and IP, active tab, online/last seen, app/Android version, uptime, storage, display geometry and screensaver, voice, camera and service status. Available light, proximity, acceleration, gyroscope, magnetic field, pressure, humidity, temperature, rotation and step sensors are created disabled.

Switches, numbers and selects control profile, brightness, screen behavior, voice/wake word, VAD, audio route, screensaver, camera FPS/quality/resolution/transport, media player and sensor interval. Buttons reload configuration, wake the screen or restart the service.

## Custom actions {#custom-actions}

| Action | Purpose |
|---|---|
| `rustyhama.send_notification` | overlay when visible, Android system notification in background |
| `rustyhama.set_active_tab` | select a tab by index or stable ID |
| `rustyhama.set_screensaver` | turn the screensaver on, off or toggle it |
| `rustyhama.reload_configuration` | send the latest published configuration |

```yaml
action: rustyhama.send_notification
data:
  device_id: 0123456789abcdef
  title: Front door
  message: Someone rang the bell.
  play_sound: true
```

Voice announcements and conversations use standard `assist_satellite` actions; playback uses `media_player`. Widgets cannot call arbitrary HA services. The integration extracts entities referenced by the effective dashboard, sends only their states, and permits a fixed typed operation set per domain.
