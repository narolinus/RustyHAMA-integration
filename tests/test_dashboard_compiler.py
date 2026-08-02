"""Contract tests for server-side dashboard compilation."""

from __future__ import annotations

from typing import Any

from custom_components.rustyhama.dashboard_compiler import DashboardCompiler


class FakeState:
    def __init__(self, entity_id: str, state: str, **attributes: Any) -> None:
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "state": self.state,
            "attributes": self.attributes,
            "last_changed": "2026-08-01T12:00:00+00:00",
            "last_updated": "2026-08-01T12:00:00+00:00",
        }


class FakeStates:
    def __init__(self, states: list[FakeState]) -> None:
        self._states = states

    def async_all(self) -> list[FakeState]:
        return self._states


class FakeHass:
    def __init__(self, states: list[FakeState]) -> None:
        self.states = FakeStates(states)


def test_compiler_resolves_auto_entities_and_keeps_only_selected_states() -> None:
    compiler = DashboardCompiler(
        FakeHass(
            [
                FakeState("light.kitchen", "on", friendly_name="Kitchen"),
                FakeState("light.hall", "off", friendly_name="Hall"),
                FakeState("sensor.temperature", "19.5", friendly_name="Temperature"),
            ]
        )
    )
    compiled = compiler.compile(
        {
            "schema_version": 1,
            "tabs": [
                {
                    "id": "home",
                    "widgets": [
                        {
                            "id": "lights",
                            "type": "auto-entities",
                            "filter": {"include": [{"domain": "light", "state": "on"}]},
                            "sort": {"method": "name"},
                            "card": {"type": "entities"},
                        }
                    ],
                }
            ],
        }
    )

    widget = compiled.config["tabs"][0]["widgets"][0]
    assert widget["server_compiled"] is True
    assert widget["entities"] == [{"entity": "light.kitchen"}]
    assert "filter" not in widget
    assert "sort" not in widget
    assert compiled.entity_ids == frozenset({"light.kitchen"})
    assert compiled.dynamic is True


def test_compiler_preserves_explicit_entries_applies_exclusion_and_sorts() -> None:
    compiler = DashboardCompiler(
        FakeHass(
            [
                FakeState("sensor.alpha", "2", friendly_name="Alpha"),
                FakeState("sensor.beta", "10", friendly_name="Beta"),
                FakeState("sensor.hidden", "42", friendly_name="Hidden"),
            ]
        )
    )
    compiled = compiler.compile(
        {
            "schema_version": 1,
            "tabs": [
                {
                    "id": "home",
                    "widgets": [
                        {
                            "id": "sensors",
                            "type": "auto_entities",
                            "entities": ["sensor.alpha"],
                            "filter": {
                                "include": [{"domain": "sensor"}],
                                "exclude": [{"entity_id": "sensor.hidden"}],
                            },
                            "unique": True,
                            "sort": {"method": "state", "numeric": True, "reverse": True},
                            "card": {"type": "entities"},
                        }
                    ],
                }
            ],
        }
    )

    entries = compiled.config["tabs"][0]["widgets"][0]["entities"]
    assert [entry["entity"] for entry in entries] == ["sensor.beta", "sensor.alpha"]
    assert compiled.entity_ids == frozenset({"sensor.alpha", "sensor.beta"})


def test_compiler_includes_entities_used_by_runtime_discovery() -> None:
    compiler = DashboardCompiler(
        FakeHass(
            [
                FakeState("calendar.family", "on", friendly_name="Family"),
                FakeState("media_player.kitchen", "idle", friendly_name="Kitchen"),
                FakeState("sensor.unrelated", "1", friendly_name="Unrelated"),
            ]
        )
    )
    compiled = compiler.compile(
        {
            "schema_version": 1,
            "tabs": [
                {"id": "calendar", "widgets": [{"type": "calendar"}]},
                {"id": "music", "type": "music_assistant", "widgets": []},
            ],
        }
    )

    assert compiled.entity_ids == frozenset(
        {"calendar.family", "media_player.kitchen"}
    )
