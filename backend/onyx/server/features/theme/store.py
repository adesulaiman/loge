from onyx.configs.constants import KV_THEME_SETTINGS_KEY
from onyx.key_value_store.factory import get_kv_store
from onyx.key_value_store.interface import KvKeyNotFoundError
from onyx.server.features.theme.models import ThemeSettings

THEME_LOGO_FILE_ID = "loge_theme_logo"


def load_theme_settings() -> ThemeSettings:
    try:
        raw = get_kv_store().load(KV_THEME_SETTINGS_KEY)
    except KvKeyNotFoundError:
        return ThemeSettings()
    if not isinstance(raw, dict):
        return ThemeSettings()
    return ThemeSettings.model_validate(raw)


def store_theme_settings(settings: ThemeSettings) -> None:
    get_kv_store().store(KV_THEME_SETTINGS_KEY, settings.model_dump())
