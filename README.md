# RustyHAMA Integration

RustyHAMA is the Home Assistant 2026.7+ integration for paired Android wall
tablets. It owns device configuration, dashboard profiles, credentials,
provider connections, typed actions and native Home Assistant entities.

Dashboard profiles are compiled server-side per device. In particular,
`auto-entities` filtering and sorting remain in Home Assistant, so old Android
devices receive only the resolved entity list and the states required to render it.

Install [narolinus/RustyHAMA-integration](https://github.com/narolinus/RustyHAMA-integration)
as a HACS custom integration, restart Home Assistant,
add **RustyHAMA** in **Settings → Devices & services**, and pair tablets from
the RustyHAMA sidebar panel. HTTP and Home Assistant user tokens are not
supported by the device protocol.

Complete and equally maintained documentation is available in
[Deutsch](docs/de/index.md), [English](docs/en/index.md) and
[Français](docs/fr/index.md). All editions live below `docs/` and share the
single asset tree in `docs/assets/`.
