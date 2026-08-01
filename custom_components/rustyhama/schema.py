"""Dashboard schema validation shared by the editor and publisher."""

from __future__ import annotations

from typing import Any


class DashboardValidationError(ValueError):
    """Raised when a dashboard cannot be published."""


def validate_dashboard(config: Any) -> list[str]:
    """Validate structural invariants and return non-fatal warnings."""
    if not isinstance(config, dict):
        raise DashboardValidationError("dashboard must be an object")
    if config.get("schema_version") != 1:
        raise DashboardValidationError("schema_version must be 1")
    tabs = config.get("tabs")
    if not isinstance(tabs, list) or not tabs:
        raise DashboardValidationError("tabs must be a non-empty array")
    identifiers: set[str] = set()

    def reject_secrets(value: Any, path: str = "dashboard") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"api_key", "password", "secret", "credential", "token"}:
                    raise DashboardValidationError(
                        f"{path}.{key} must be stored as a provider connection"
                    )
                reject_secrets(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_secrets(child, f"{path}[{index}]")

    reject_secrets(config)

    def require_id(item: Any, path: str) -> None:
        if not isinstance(item, dict):
            raise DashboardValidationError(f"{path} must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise DashboardValidationError(f"{path}.id is required")
        if identifier in identifiers:
            raise DashboardValidationError(f"duplicate id: {identifier}")
        identifiers.add(identifier)

    for tab_index, tab in enumerate(tabs):
        require_id(tab, f"tabs[{tab_index}]")
        widgets = tab.get("widgets", [])
        if not isinstance(widgets, list):
            raise DashboardValidationError(f"tabs[{tab_index}].widgets must be an array")
        for widget_index, widget in enumerate(widgets):
            require_id(widget, f"tabs[{tab_index}].widgets[{widget_index}]")
            if not isinstance(widget.get("type"), str):
                raise DashboardValidationError(
                    f"tabs[{tab_index}].widgets[{widget_index}].type is required"
                )
    return []


def referenced_providers(config: Any) -> set[str]:
    """Collect explicit provider/connection references from a dashboard."""
    found: set[str] = set()

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and key in {
            "provider_id",
            "connection_id",
            "immich_connection",
            "music_assistant_connection",
        }:
            found.add(value)

    visit(config)
    return found
