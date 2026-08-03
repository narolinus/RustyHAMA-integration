# RustyHAMA Integration

![RustyHAMA](custom_components/rustyhama/brand/logo.png)

RustyHAMA is the Home Assistant 2026.7+ integration for paired Android wall
tablets. It owns device configuration, dashboard profiles, credentials,
provider connections, typed actions and native Home Assistant entities.

> This GitHub repository is the public HACS mirror. Development and support are
> maintained in [Forgejo](https://dev.spittank.org/daniel/RustyHAMA-Integration).
> GitHub Issues and Discussions are intentionally disabled.

Dashboard profiles are compiled server-side per device. In particular,
`auto-entities` filtering and sorting remain in Home Assistant, so old Android
devices receive only the resolved entity list and the states required to render it.

Install [narolinus/RustyHAMA-integration](https://github.com/narolinus/RustyHAMA-integration)
as a HACS custom integration, restart Home Assistant,
add **RustyHAMA** in **Settings → Devices & services**, and pair tablets from
the RustyHAMA sidebar panel. HTTP and Home Assistant user tokens are not
supported by the device protocol.

The complete, equally maintained documentation is published from the Android
application repository:

- [Deutsch](https://daniel.snii.de/RustyHAMA/)
- [English](https://daniel.snii.de/RustyHAMA/en/)
- [Français](https://daniel.snii.de/RustyHAMA/fr/)

[Source documentation and application repository](https://dev.spittank.org/daniel/RustyHAMA)
