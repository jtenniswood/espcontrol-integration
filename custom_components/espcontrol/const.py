"""Integration identifiers and generated catalog field rules."""

from __future__ import annotations

from dataclasses import dataclass

from .catalog_contract import FIELD_DOMAINS, TRANSPORTS

DOMAIN = "espcontrol"
MIRROR_PLATFORMS = (
    "sensor",
    "binary_sensor",
    "light",
    "button",
    "switch",
    "select",
    "number",
    "text",
)
CONF_DEVICE_ID = "device_id"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_WEB_PORT = "web_port"
CONF_MODEL = "model"
CONF_PROTOCOL = "protocol"
CONF_MAC = "mac"

DEFAULT_PORT = 6053
PROTOCOL_VERSION = 1
PAIRING_TOKEN_HEADER = "Authorization"
PAIRING_TOKEN_TTL_SECONDS = 600

SERVICE_CREATE_PAIRING_TOKEN = "create_pairing_token"
SERVICE_SEARCH_ENTITIES = "search_entities"


@dataclass(frozen=True, slots=True)
class EntityRule:
    """The Home Assistant entities accepted by one EspControl field."""

    domains: frozenset[str] | None = None
    capabilities: frozenset[str] = frozenset()
    allow_any_domain: bool = False


DEFAULT_CATALOG_LIMIT = TRANSPORTS["legacy_http"]["default_limit"]
MAX_CATALOG_LIMIT = TRANSPORTS["legacy_http"]["max_limit"]
ENTITY_RULES = {
    name: EntityRule(
        frozenset(domains) if domains else None, allow_any_domain=domains is None
    )
    for name, domains in FIELD_DOMAINS.items()
}
