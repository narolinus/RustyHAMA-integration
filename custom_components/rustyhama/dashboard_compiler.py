"""Compile declarative dashboards into small, device-specific view models."""

from __future__ import annotations

import fnmatch
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

AUTO_ENTITY_TYPES = frozenset({"auto_entities", "auto-entities", "custom:auto-entities"})
ENTITY_KEYS = frozenset({"entity", "entity_id"})
_NUMBER = re.compile(r"^(<=|>=|!=|!|=|<|>)\s*(-?\d+(?:\.\d+)?)$")
_DURATION = re.compile(r"^(<=|>=|!=|!|=|<|>)?\s*(\d+(?:\.\d+)?)\s*([smhdw])?(?:\s+ago)?$")


@dataclass(frozen=True, slots=True)
class Compilation:
    """A server-resolved dashboard and the narrow state subscription it needs."""

    config: dict[str, Any]
    entity_ids: frozenset[str]
    dynamic: bool
    fingerprint: str


class DashboardCompiler:
    """Resolve expensive entity queries while preserving the widget contract."""

    def __init__(self, hass: Any) -> None:
        self.hass = hass

    def compile(self, config: dict[str, Any], area_id: str | None = None) -> Compilation:
        """Return a copy whose auto-entities widgets contain concrete entity lists."""
        states = {
            state.entity_id: state.as_dict()
            for state in self.hass.states.async_all()
        }
        metadata = {entity_id: self._metadata(entity_id, area_id) for entity_id in states}
        result = deepcopy(config)
        selected: set[str] = set()
        dynamic = False

        def visit(value: Any) -> None:
            nonlocal dynamic
            if isinstance(value, dict):
                if str(value.get("type", "")).lower() in AUTO_ENTITY_TYPES:
                    entries, is_dynamic = self._resolve_auto_entities(value, states, metadata)
                    value["entities"] = entries
                    value.pop("filter", None)
                    value.pop("sort", None)
                    value.pop("unique", None)
                    value["server_compiled"] = True
                    selected.update(self._entity_id(entry) for entry in entries)
                    dynamic = dynamic or is_dynamic
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(result)
        selected.update(self._explicit_entity_references(result))
        selected.update(self._implicit_entity_references(result, states))
        selected.discard("")
        encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return Compilation(result, frozenset(selected), dynamic, encoded)

    def _implicit_entity_references(
        self, config: dict[str, Any], states: dict[str, dict[str, Any]]
    ) -> set[str]:
        """Select state families used by widgets that intentionally auto-discover."""
        domains: set[str] = set()

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                widget_type = str(value.get("type", "")).lower()
                if widget_type == "calendar":
                    domains.add("calendar")
                # Media controls discover groupable players; the MA tab maps MA
                # player IDs to HA media_player entities at runtime.
                if widget_type in {"media", "media_player", "music_assistant"}:
                    domains.add("media_player")
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(config)
        return {
            entity_id
            for entity_id in states
            if entity_id.partition(".")[0] in domains
        }

    def _metadata(self, entity_id: str, default_area: str | None) -> dict[str, Any]:
        """Expose HA registry selectors without ever exposing registries to Android."""
        metadata: dict[str, Any] = {"area": default_area or "", "device": "", "integration": "", "labels": set()}
        try:
            from homeassistant.helpers import device_registry as dr
            from homeassistant.helpers import entity_registry as er

            entity = er.async_get(self.hass).async_get(entity_id)
            if entity is None:
                return metadata
            metadata["device"] = entity.device_id or ""
            metadata["area"] = entity.area_id or metadata["area"]
            metadata["integration"] = entity.platform or ""
            metadata["labels"] = set(getattr(entity, "labels", ()) or ())
            if entity.device_id:
                device = dr.async_get(self.hass).async_get(entity.device_id)
                if device is not None:
                    metadata["area"] = metadata["area"] or device.area_id or ""
                    metadata["labels"].update(getattr(device, "labels", ()) or ())
        except (AttributeError, ImportError):
            # Unit tests and partially initialized HA instances may not have registries yet.
            pass
        return metadata

    def _resolve_auto_entities(
        self,
        config: dict[str, Any],
        states: dict[str, dict[str, Any]],
        metadata: dict[str, dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], bool]:
        entries = self._explicit_entries(config.get("entities"), states)
        query = config.get("filter")
        dynamic = isinstance(query, dict) or isinstance(config.get("sort"), dict)
        if isinstance(query, dict):
            for rule in query.get("include", []) or []:
                normalized = self._rule(rule)
                matched = [
                    self._entry(entity_id, normalized.get("options"), states[entity_id])
                    for entity_id in sorted(states)
                    if self._matches(normalized, entity_id, states[entity_id], metadata[entity_id])
                ]
                self._sort(matched, normalized.get("sort"))
                entries.extend(matched)
            excludes = [self._rule(rule) for rule in query.get("exclude", []) or []]
            entries = [
                entry
                for entry in entries
                if not any(
                    self._matches(rule, self._entity_id(entry), states.get(self._entity_id(entry)), metadata.get(self._entity_id(entry), {}))
                    for rule in excludes
                )
            ]
        if config.get("unique"):
            unique: dict[str, dict[str, Any]] = {}
            for entry in entries:
                unique[self._entity_id(entry)] = entry
            entries = list(unique.values())
        self._sort(entries, config.get("sort"))
        return entries, dynamic

    @staticmethod
    def _rule(value: Any) -> dict[str, Any]:
        return {"entity_id": value} if isinstance(value, str) else dict(value or {})

    def _explicit_entries(
        self, values: Any, states: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            self._entry(self._entity_id(value), value if isinstance(value, dict) else None, states.get(self._entity_id(value)))
            for value in (values or [])
            if self._entity_id(value)
        ]

    @staticmethod
    def _entry(entity_id: str, options: Any, state: dict[str, Any] | None) -> dict[str, Any]:
        entry = deepcopy(options) if isinstance(options, dict) else {}
        entry["entity"] = entity_id
        if state is not None:
            entry.pop("entity_id", None)
        return entry

    @staticmethod
    def _entity_id(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get("entity", value.get("entity_id", "")))
        return ""

    def _matches(
        self, rule: dict[str, Any], entity_id: str, state: dict[str, Any] | None, metadata: dict[str, Any]
    ) -> bool:
        if state is None:
            return False
        if "or" in rule and not any(
            self._matches(self._rule(item), entity_id, state, metadata) for item in rule["or"] or []
        ):
            return False
        if "and" in rule and not all(
            self._matches(self._rule(item), entity_id, state, metadata) for item in rule["and"] or []
        ):
            return False
        if "not" in rule and self._matches(self._rule(rule["not"]), entity_id, state, metadata):
            return False
        for raw_key, expected in rule.items():
            key = str(raw_key).split(maxsplit=1)[0]
            if key in {"options", "sort", "or", "and", "not", "type"}:
                continue
            if key == "entity_id" and not self._matches_value(entity_id, expected):
                return False
            if key == "domain" and not self._matches_value(entity_id.partition(".")[0], expected):
                return False
            if key == "state" and not self._matches_value(str(state.get("state", "")), expected):
                return False
            if key == "name" and not self._matches_value(str(self._value(state, "friendly_name") or ""), expected):
                return False
            if key == "attributes":
                if not isinstance(expected, dict) or any(
                    not self._matches_value(str(self._value(state, name) or ""), wanted)
                    for name, wanted in expected.items()
                ):
                    return False
            if key in {"area", "device", "integration"} and not self._matches_value(str(metadata.get(key, "")), expected):
                return False
            if key == "label" and not any(
                self._matches_value(str(label), expected) for label in metadata.get("labels", set())
            ):
                return False
            if key in {"last_changed", "last_updated"} and not self._matches_elapsed(str(state.get(key, "")), expected):
                return False
            if key not in {"entity_id", "domain", "state", "name", "attributes", "area", "device", "integration", "label", "last_changed", "last_updated"}:
                return False
        return True

    @staticmethod
    def _matches_value(actual: str, expected: Any) -> bool:
        pattern = str(expected)
        if pattern.startswith("/") and pattern.endswith("/") and len(pattern) > 2:
            try:
                return re.search(pattern[1:-1], actual) is not None
            except re.error:
                return False
        numeric = _NUMBER.fullmatch(pattern.strip())
        if numeric:
            try:
                return DashboardCompiler._compare(float(actual), numeric.group(1), float(numeric.group(2)))
            except ValueError:
                return False
        return fnmatch.fnmatchcase(actual, pattern) if any(char in pattern for char in "*?") else actual == pattern

    @staticmethod
    def _matches_elapsed(timestamp: str, expected: Any) -> bool:
        match = _DURATION.fullmatch(str(expected).strip().lower())
        if match is None:
            return False
        try:
            value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elapsed = (datetime.now(UTC) - value.astimezone(UTC)).total_seconds()
        except ValueError:
            return False
        multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}.get(match.group(3) or "m", 60)
        return DashboardCompiler._compare(elapsed, match.group(1) or "=", float(match.group(2)) * multiplier)

    @staticmethod
    def _compare(actual: float, operator: str, expected: float) -> bool:
        return {
            "<": actual < expected,
            "<=": actual <= expected,
            ">": actual > expected,
            ">=": actual >= expected,
            "=": actual == expected,
            "!": actual != expected,
            "!=": actual != expected,
        }[operator]

    @staticmethod
    def _value(state: dict[str, Any], selector: str) -> Any:
        if selector in {"name", "friendly_name"}:
            return state.get("attributes", {}).get("friendly_name")
        if selector == "object_id":
            return str(state.get("entity_id", "")).partition(".")[2]
        value: Any = state if selector in state else state.get("attributes", {})
        for part in selector.replace(":", ".").split("."):
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
        return value

    def _sort(self, entries: list[dict[str, Any]], sort: Any) -> None:
        if not isinstance(sort, dict) or len(entries) < 2:
            return
        method = str(sort.get("method", "entity_id"))
        attribute = str(sort.get("attribute", ""))
        states = {state.entity_id: state.as_dict() for state in self.hass.states.async_all()}

        def key(entry: dict[str, Any]) -> tuple[int, Any]:
            entity_id = self._entity_id(entry)
            state = states.get(entity_id, {})
            value: Any
            if method == "domain":
                value = entity_id.partition(".")[0]
            elif method == "name":
                value = self._value(state, "friendly_name") or entity_id
            elif method == "state":
                value = state.get("state", "")
            elif method == "attribute":
                value = self._value(state, attribute) or ""
            elif method in {"last_changed", "last_updated"}:
                value = state.get(method, "")
            else:
                value = entity_id
            if sort.get("numeric"):
                try:
                    return (0, float(value))
                except (TypeError, ValueError):
                    return (1, 0.0)
            return (0, str(value).lower() if sort.get("ignore_case") else str(value))

        entries.sort(key=key, reverse=bool(sort.get("reverse")))
        first = max(0, int(sort.get("first", 0)))
        count = sort.get("count")
        entries[:] = entries[first:] if count is None else entries[first : first + max(0, int(count))]

    def _explicit_entity_references(self, value: Any, key: str = "") -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for child_key, child in value.items():
                found.update(self._explicit_entity_references(child, child_key))
        elif isinstance(value, list):
            for child in value:
                found.update(self._explicit_entity_references(child, key))
        elif isinstance(value, str) and (key in ENTITY_KEYS or "." in value):
            found.add(value)
        return found
