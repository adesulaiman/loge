import functools
import importlib
import importlib.util
import inspect
from importlib.machinery import ModuleSpec
from typing import Any, TypeVar

from onyx.configs.app_configs import (
    API_SERVER_HOST,
    API_SERVER_PROTOCOL,
    API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS,
    APP_API_PREFIX,
    APP_PORT,
    DEV_MODE,
)
from onyx.utils.logger import setup_logger

logger = setup_logger()


class OnyxVersion:
    def __init__(self) -> None:
        self._is_ee = False

    def set_ee(self) -> None:
        self._is_ee = True

    def unset_ee(self) -> None:
        self._is_ee = False

    def is_ee_version(self) -> bool:
        """True when the full Loge feature package (`loge`) is loaded."""
        return self._is_ee


global_version = OnyxVersion()


def _full_feature_module_name(module: str) -> str:
    """Map a CE module path (`onyx.*`) to the full-feature package (`loge.*`)."""
    if module == "onyx":
        return "loge"
    if module.startswith("onyx."):
        return "loge." + module.removeprefix("onyx.")
    return module


def is_ee_available() -> bool:
    """Whether this build ships the full Loge feature package.

    Requires `loge.main` (not a bare `loge` stub) so MIT-only mirrors that leave
    an empty `backend/loge/__init__.py` still run as core-only.
    """
    try:
        spec: ModuleSpec | None = importlib.util.find_spec("loge.main")
    except ModuleNotFoundError:
        return False
    # A leftover directory with no `__init__.py` resolves as a namespace
    # package, which has no origin.
    return spec is not None and spec.origin is not None


def set_is_ee_if_available() -> None:
    """Load full Loge features when the `loge` package is present. Loading
    unlocks nothing: paid features stay gated on the license."""
    if global_version.is_ee_version() or not is_ee_available():
        return

    logger.notice(
        "Loge full feature package is loaded. Paid features stay locked until a "
        "valid license is applied."
    )
    global_version.set_ee()


@functools.lru_cache(maxsize=128)
def fetch_versioned_implementation(module: str, attribute: str) -> Any:
    """
    Fetches a versioned implementation of a specified attribute from a given module.
    When the full Loge feature package is loaded, prefer `loge.*` over `onyx.*`.
    If the full-feature symbol is missing, fall back to the CE module.
    """
    logger.debug("Fetching versioned implementation for %s.%s", module, attribute)
    is_ee = global_version.is_ee_version()

    module_full = _full_feature_module_name(module) if is_ee else module
    try:
        return getattr(  # ods: ignore[getattr]
            importlib.import_module(module_full), attribute
        )
    except ModuleNotFoundError as e:
        logger.warning(
            "Failed to fetch versioned implementation for %s.%s: %s",
            module_full,
            attribute,
            e,
        )

        if is_ee:
            if "loge" not in str(e):
                # Non-loge import failure: likely a missing dependency. Raise.
                raise e

            # Fall back to the CE module when a loge override is absent.
            return getattr(  # ods: ignore[getattr]
                importlib.import_module(module), attribute
            )

        raise


T = TypeVar("T")


def fetch_versioned_implementation_with_fallback(
    module: str, attribute: str, fallback: T
) -> T:
    """
    Attempts to fetch a versioned implementation of a specified attribute from a given module.
    If the attempt fails (e.g., due to an import error or missing attribute), the function logs
    a warning and returns the provided fallback implementation.
    """
    try:
        return fetch_versioned_implementation(module, attribute)
    except Exception:
        return fallback


def noop_fallback(*args: Any, **kwargs: Any) -> None:
    """
    A no-op (no operation) fallback function that accepts any arguments but does nothing.
    """


def fetch_ee_implementation_or_noop(
    module: str, attribute: str, noop_return_value: Any = None
) -> Any:
    """
    Fetches a full-feature implementation if loaded, otherwise returns a no-op function.
    Raises an exception if full features are loaded but the fetch fails.
    """
    if not global_version.is_ee_version():
        if inspect.iscoroutinefunction(noop_return_value):

            async def async_noop(*args: Any, **kwargs: Any) -> Any:
                return await noop_return_value(*args, **kwargs)

            return async_noop

        else:

            def sync_noop(*args: Any, **kwargs: Any) -> Any:  # noqa: ARG001
                return noop_return_value

            return sync_noop
    try:
        return fetch_versioned_implementation(module, attribute)
    except Exception as e:
        logger.error(
            "Failed to fetch implementation for %s.%s: %s", module, attribute, e
        )
        raise


def build_api_server_url_for_http_requests(
    respect_env_override_if_set: bool = False,
) -> str:
    """
    Builds the API server URL for HTTP requests.
    """
    if DEV_MODE:
        url = f"http://127.0.0.1:{APP_PORT}"
    elif respect_env_override_if_set and API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS:
        url = API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS.rstrip("/")
    else:
        url = f"{API_SERVER_PROTOCOL}://{API_SERVER_HOST}:{APP_PORT}"

    if APP_API_PREFIX:
        url += f"/{APP_API_PREFIX.strip('/')}"

    return url
