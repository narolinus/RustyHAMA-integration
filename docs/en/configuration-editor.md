# Configuration and editor {#configuration-and-editor}

## Profiles, overrides and effective configuration {#profiles-overrides-and-effective-configuration}

A profile contains a complete dashboard. A device references one profile and may store an override. It follows RFC 7396: objects merge recursively, arrays are replaced in full, and `null` removes a key. Provider bindings are stored separately and are never resolved to secrets.

```json
{
  "schema_version": 1,
  "theme": "dark",
  "tabs": [
    {
      "id": "overview",
      "title": "Overview",
      "columns": 2,
      "widgets": [{"id": "clock", "type": "clock"}]
    }
  ]
}
```

## JSON and visual editor {#json-and-visual-editor}

JSON is always the default view. Separate views show the profile draft, device override and read-only effective configuration. Saving creates a draft; only **Publish** validates references, creates a monotonic revision and deploys it. Missing providers block publishing. Temporarily missing HA entities produce warnings.

The visual editor changes themes, tabs, columns and common native widgets. Unknown or complex blocks remain unchanged, so switching back to JSON never loses advanced content.

## Preview {#preview}

Select a device to use its last reported physical and usable pixel size, activity content area, orientation, density, density DPI, font scale and known insets. The preview converts dp and sp with those values and scales proportionally into the browser. Portrait and landscape can be switched deliberately. Offline devices use their last data; the generic tablet is explicitly not device-specific.

The preview uses current HA states but remains an approximation because Android and browser font engines differ. The native device is authoritative.

## Revisions and rollback {#revisions-and-rollback}

Twenty immutable revisions are retained. A rollback does not rewrite history; it republishes the chosen content as a newer revision. If the app rejects a configuration, its last valid configuration stays active and HA shows the unacknowledged revision.
