"""Read-only mirrors of sensors owned by the panel's native ESPHome entry."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_ICON, STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_DEVICE_ID, DOMAIN, SIGNAL_ESPHOME_ENTITIES_UPDATED
from .device import ESPHOME_DOMAIN, find_esphome_device, mac_from_entry


def mirror_unique_id(entry: ConfigEntry, source: er.RegistryEntry) -> str:
    """Use the native unique ID, which survives user entity-ID changes."""

    return f"{entry.data[CONF_DEVICE_ID]}_{source.domain}_{source.unique_id}"


class EspControlMirror(Entity):
    """Share source tracking, metadata and availability across sensor types."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, source: er.RegistryEntry) -> None:
        self._source: er.RegistryEntry | None = source
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

    def _state(self) -> State | None:
        if self._source is None:
            return None
        return self.hass.states.get(self._source.entity_id)

    @property
    def available(self) -> bool:
        state = self._state()
        return state is not None and state.state != STATE_UNAVAILABLE

    @property
    def name(self) -> str:
        state = self._state()
        return (
            state.attributes.get(ATTR_FRIENDLY_NAME, self._source_name)
            if state
            else self._source_name
        )

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
    """Discover sensors even if ESPHome is added or reloaded after startup."""

    registry = er.async_get(hass)
    mirrors: dict[str, EspControlMirror] = {}

    @callback
    def reconcile(_event: Event | None = None) -> None:
        mac = mac_from_entry(entry)
        device = find_esphome_device(hass, mac) if mac else None
        sources = (
            {
                mirror_unique_id(entry, source): source
                for source in er.async_entries_for_device(registry, device.id)
                if source.domain == domain
                and source.platform == ESPHOME_DOMAIN
                and source.config_entry_id == device.config_entry_id
                and not source.disabled
            }
            if device
            else {}
        )

        for unique_id, mirror in mirrors.items():
            mirror.async_set_source(sources.get(unique_id))

        additions = []
        for unique_id, source in sources.items():
            if unique_id in mirrors:
                continue
            # Preserve entity IDs, history and customizations from the draft,
            # whose unique IDs included the editable source entity ID.
            if registry.async_get_entity_id(domain, DOMAIN, unique_id) is None:
                legacy_id = registry.async_get_entity_id(
                    domain, DOMAIN, f"{entry.data[CONF_DEVICE_ID]}_{source.entity_id}"
                )
                if (
                    legacy_id
                    and registry.async_get(legacy_id).config_entry_id == entry.entry_id
                ):
                    registry.async_update_entity(legacy_id, new_unique_id=unique_id)
            mirror = factory(entry, source)
            mirrors[unique_id] = mirror
            additions.append(mirror)
        if additions:
            async_add_entities(additions)

    for event_type in (
        er.EVENT_ENTITY_REGISTRY_UPDATED,
        dr.EVENT_DEVICE_REGISTRY_UPDATED,
    ):
        entry.async_on_unload(hass.bus.async_listen(event_type, reconcile))
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_ESPHOME_ENTITIES_UPDATED, reconcile)
    )
    reconcile()
