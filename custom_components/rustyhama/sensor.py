"""RustyHAMA sensor entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import RustyEntity, async_setup_dynamic_entities, nested_value
from .models import DeviceRecord


@dataclass(frozen=True, slots=True)
class SensorSpec:
    key: str
    name: str
    path: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    enabled: bool = True
    category: EntityCategory | None = EntityCategory.DIAGNOSTIC


SENSORS = (
    SensorSpec("battery", "Battery", "battery_level", PERCENTAGE, SensorDeviceClass.BATTERY),
    SensorSpec("power_source", "Power source", "power_source"),
    SensorSpec("wifi_signal", "Wi-Fi signal", "wifi_signal_dbm", "dBm", SensorDeviceClass.SIGNAL_STRENGTH),
    SensorSpec("network", "Network", "network_type"),
    SensorSpec("ip_address", "IP address", "ip_address"),
    SensorSpec("active_tab", "Active tab", "active_tab", category=None),
    SensorSpec("last_seen", "Last seen", "last_seen", device_class=SensorDeviceClass.TIMESTAMP),
    SensorSpec("app_version", "App version", "app_version"),
    SensorSpec("android_version", "Android version", "android_version"),
    SensorSpec("uptime", "Uptime", "uptime_seconds", UnitOfTime.SECONDS, SensorDeviceClass.DURATION),
    SensorSpec("free_storage", "Free storage", "free_storage_bytes", "B", SensorDeviceClass.DATA_SIZE),
    SensorSpec("display_width", "Display width", "display.usable_width_px", "px"),
    SensorSpec("display_height", "Display height", "display.usable_height_px", "px"),
    SensorSpec("display_density", "Display density", "display.density_dpi", "dpi"),
)


class RustySensor(RustyEntity, SensorEntity):
    """One device telemetry sensor."""

    def __init__(self, manager: Any, device: DeviceRecord, spec: SensorSpec) -> None:
        super().__init__(manager, device, spec.key)
        self.spec = spec
        self._attr_name = spec.name
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_entity_category = spec.category
        self._attr_entity_registry_enabled_default = spec.enabled

    @property
    def native_value(self) -> Any:
        source = {**self.device.telemetry, "display": self.device.display}
        if self.spec.key == "last_seen":
            return self.device.last_seen
        return nested_value(source, self.spec.path)


def _entities(manager: Any, device: DeviceRecord) -> list[RustySensor]:
    entities = [RustySensor(manager, device, spec) for spec in SENSORS]
    for sensor in device.capabilities.get("sensors", []):
        if not isinstance(sensor, dict) or not sensor.get("type"):
            continue
        sensor_type = str(sensor["type"])
        entities.append(
            RustySensor(
                manager,
                device,
                SensorSpec(
                    f"hardware_{sensor_type}",
                    str(sensor.get("name") or sensor_type.replace("_", " ").title()),
                    f"sensors.{sensor_type}",
                    sensor.get("unit"),
                    enabled=False,
                ),
            )
        )
    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    await async_setup_dynamic_entities(entry.runtime_data.manager, async_add_entities, _entities)
