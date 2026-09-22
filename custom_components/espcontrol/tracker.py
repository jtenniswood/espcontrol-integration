"""One filtered native-source tracker shared by all platforms of a display."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import MIRROR_PLATFORMS
from .device import ESPHOME_DOMAIN, find_esphome_device, mac_from_entry, webserver_url


class NativeSourceTracker:
    """Reconcile only changes involving this display's native ESPHome device."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, host: str, port: int
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.mac = mac_from_entry(entry)
        self.configuration_url = webserver_url(host, port)
        self.device_id: str | None = None
        self.sources: dict[str, er.RegistryEntry] = {}
        self._known_entities: set[str] = set()
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribers: list[Callable[[], None]] = []

    @property
    def available_sources(self) -> int:
        return sum(
            1
            for source in self.sources.values()
            if (state := self.hass.states.get(source.entity_id)) is not None
            and state.state != STATE_UNAVAILABLE
        )

    @callback
    def async_start(self) -> None:
        self._unsubscribers = [
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._entity_changed
            ),
            self.hass.bus.async_listen(
                dr.EVENT_DEVICE_REGISTRY_UPDATED, self._device_changed
            ),
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._started),
        ]
        self.async_reconcile()

    @callback
    def async_stop(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._listeners.clear()

    @callback
    def async_subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        listener()

        @callback
        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    @callback
    def _started(self, _event: Event) -> None:
        self.async_reconcile()

    @callback
    def _entity_changed(self, event: Event) -> None:
        entity_id = event.data["entity_id"]
        old_id = event.data.get("old_entity_id")
        source = er.async_get(self.hass).async_get(entity_id)
        if (
            entity_id in self._known_entities
            or old_id in self._known_entities
            or (
                source is not None
                and source.platform == ESPHOME_DOMAIN
                and source.device_id == self.device_id
                and self.device_id is not None
            )
        ):
            self.async_reconcile()

    @callback
    def _device_changed(self, event: Event) -> None:
        device_id = event.data["device_id"]
        device = dr.async_get(self.hass).async_get(device_id)
        if device_id == self.device_id or (
            device is not None
            and self.mac is not None
            and (dr.CONNECTION_NETWORK_MAC, self.mac) in device.connections
            and (
                owner := self.hass.config_entries.async_get_entry(
                    device.config_entry_id
                )
            )
            and owner.domain == ESPHOME_DOMAIN
        ):
            self.async_reconcile()

    @callback
    def async_reconcile(self) -> None:
        device = find_esphome_device(self.hass, self.mac) if self.mac else None
        self.device_id = device.id if device else None
        sources = (
            [
                source
                for source in er.async_entries_for_device(
                    er.async_get(self.hass), device.id
                )
                if source.platform == ESPHOME_DOMAIN
                and source.config_entry_id == device.config_entry_id
                and source.domain in MIRROR_PLATFORMS
            ]
            if device
            else []
        )
        self._known_entities = {source.entity_id for source in sources}
        self.sources = {source.id: source for source in sources if not source.disabled}
        if device and device.configuration_url != self.configuration_url:
            dr.async_get(self.hass).async_update_device(
                device.id, configuration_url=self.configuration_url
            )
        for listener in tuple(self._listeners):
            listener()
