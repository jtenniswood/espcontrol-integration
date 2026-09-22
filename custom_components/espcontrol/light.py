"""Mirror the panel backlight and other native ESPHome lights."""

from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlToggleMirror
from .mirror import async_setup_mirrors


class EspControlLightMirror(EspControlToggleMirror, LightEntity):
    """Preserve native brightness, color and effect capabilities."""

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return {
            ColorMode(mode)
            for mode in self.source_attribute(
                "supported_color_modes", [ColorMode.ONOFF]
            )
        }

    @property
    def color_mode(self) -> ColorMode | None:
        mode = self.source_attribute("color_mode")
        return ColorMode(mode) if mode else None

    @property
    def supported_features(self) -> LightEntityFeature:
        return LightEntityFeature(self.source_attribute("supported_features", 0))

    @property
    def brightness(self) -> int | None:
        return self.source_attribute("brightness")

    @property
    def color_temp_kelvin(self) -> int | None:
        return self.source_attribute("color_temp_kelvin")

    @property
    def min_color_temp_kelvin(self) -> int:
        return self.source_attribute("min_color_temp_kelvin", 2000)

    @property
    def max_color_temp_kelvin(self) -> int:
        return self.source_attribute("max_color_temp_kelvin", 6535)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        return self.source_attribute("hs_color")

    @property
    def xy_color(self) -> tuple[float, float] | None:
        return self.source_attribute("xy_color")

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self.source_attribute("rgb_color")

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        return self.source_attribute("rgbw_color")

    @property
    def rgbww_color(self) -> tuple[int, int, int, int, int] | None:
        return self.source_attribute("rgbww_color")

    @property
    def effect(self) -> str | None:
        return self.source_attribute("effect")

    @property
    def effect_list(self) -> list[str] | None:
        return self.source_attribute("effect_list")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(hass, entry, "light", EspControlLightMirror, async_add_entities)
