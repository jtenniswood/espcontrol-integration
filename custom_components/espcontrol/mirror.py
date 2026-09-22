"""Mirrors of entities owned by the panel's native ESPHome entry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_DEVICE_ID, DOMAIN
from .migrations import async_migrate_mirror


def mirror_unique_id(entry: ConfigEntry, source: er.RegistryEntry) -> str:
    """Use the native unique ID, which survives user entity-ID changes."""

    return f"{entry.data[CONF_DEVICE_ID]}_{source.domain}_{source.unique_id}"


class EspControlMirror(Entity):
    """Share source tracking, metadata and availability across entity types."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, source: er.RegistryEntry) -> None:
        self._source: er.RegistryEntry | None = source
        self._source_entity_id = source.entity_id
        self._source_name = source.name or source.original_name or source.entity_id
        self._entry = entry
        self._attr_unique_id = mirror_unique_id(entry, source)
        self._attr_entity_category = source.entity_category
        self._unsubscribe_source: Callable[[], None] | None = None
        self._listening = False

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data[CONF_DEVICE_ID])},
            name=self._entry.title,
            manufacturer="EspControl",
            model=self._entry.data.get("model"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Preserve explicit source lineage without changing catalog wire v1."""
        return {"source_entity_id": self._source_entity_id}

    def _state(self) -> State | None:
        if self._source is None:
            return None
        return self.hass.states.get(self._source.entity_id)

    def source_attribute(self, name: str, default: Any = None) -> Any:
        """Read current native metadata, including capabilities learned later."""
        state = self._state()
        return state.attributes.get(name, default) if state else default

    @property
    def source_value(self) -> str | None:
        state = self._state()
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None
        return state.state

    @property
    def available(self) -> bool:
        state = self._state()
        return state is not None and state.state != STATE_UNAVAILABLE

    @property
    def name(self) -> str | None:
        if (source := self._source) is None:
            return self._source_name
        # ESPHome already stores the short entity name in the registry. Its
        # state friendly_name includes the device prefix and must not be reused.
        name = source.name or source.original_name
        if not source.has_entity_name:
            name = name or self.source_attribute(ATTR_FRIENDLY_NAME, source.entity_id)
            device = (
                dr.async_get(self.hass).async_get(source.device_id)
                if source.device_id
                else None
            )
            if device:
                for prefix in (device.name_by_user, device.name):
                    if prefix and name.startswith(f"{prefix} "):
                        name = name[len(prefix) + 1 :]
                        break
        self._source_name = name
        return name

    @property
    def icon(self) -> str | None:
        state = self._state()
        return state.attributes.get(ATTR_ICON) if state else None

    @callback
    def async_set_source(self, source: er.RegistryEntry | None) -> None:
        """Follow renames and mark removed or disabled sources unavailable."""

        if source == self._source:
            return
        self._source = source
        if source is not None:
            self._source_entity_id = source.entity_id
            self._source_name = source.name or source.original_name or source.entity_id
            self._attr_entity_category = source.entity_category
        if self._listening:
            self._subscribe()
            self.async_write_ha_state()

    @callback
    def _subscribe(self) -> None:
        if self._unsubscribe_source is not None:
            self._unsubscribe_source()
            self._unsubscribe_source = None
        if self._source is not None:
            self._unsubscribe_source = async_track_state_change_event(
                self.hass, [self._source.entity_id], self._source_updated
            )

    @callback
    def _source_updated(self, _event: Event) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._listening = True
        self._subscribe()

    async def async_will_remove_from_hass(self) -> None:
        self._listening = False
        if self._unsubscribe_source is not None:
            self._unsubscribe_source()
            self._unsubscribe_source = None
        await super().async_will_remove_from_hass()


@callback
def async_setup_mirrors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    domain: str,
    factory: Callable[[ConfigEntry, er.RegistryEntry], EspControlMirror],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Discover entities even if ESPHome is added or reloaded after startup."""

    registry = er.async_get(hass)
    mirrors: dict[str, EspControlMirror] = {}

    tracker = entry.runtime_data.sources

    @callback
    def reconcile() -> None:
        sources = {
            mirror_unique_id(entry, source): source
            for source in tracker.sources.values()
            if source.domain == domain
        }
        for unique_id, mirror in mirrors.items():
            mirror.async_set_source(sources.get(unique_id))
        additions = []
        for unique_id, source in sources.items():
            if unique_id in mirrors:
                continue
            async_migrate_mirror(registry, entry, source, unique_id)
            mirror = factory(entry, source)
            mirrors[unique_id] = mirror
            additions.append(mirror)
        if additions:
            async_add_entities(additions)

    entry.async_on_unload(tracker.async_subscribe(reconcile))
