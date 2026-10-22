import io

from fastapi import APIRouter, Depends, File, Response, UploadFile

from onyx.auth.permissions import require_permission
from onyx.configs.constants import FileOrigin
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.file_store.file_store import get_default_file_store
from onyx.server.features.theme.models import ThemeSettings
from onyx.server.features.theme.store import (
    THEME_LOGO_FILE_ID,
    load_theme_settings,
    store_theme_settings,
)

# SVG is excluded on purpose: it can carry script.
ALLOWED_LOGO_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024

router = APIRouter(prefix="/theme")
admin_router = APIRouter(prefix="/admin/theme")


@router.get("")
def get_theme() -> ThemeSettings:
    return load_theme_settings()


@router.get("/logo")
def get_theme_logo() -> Response:
    logo = get_default_file_store().get_file_with_mime_type(THEME_LOGO_FILE_ID)
    if logo is None or logo.mime_type not in ALLOWED_LOGO_MIME_TYPES:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "No custom logo set")
    return Response(content=logo.data, media_type=logo.mime_type)


@admin_router.put("")
def put_theme(
    settings: ThemeSettings,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> ThemeSettings:
    store_theme_settings(settings)
    return settings


@admin_router.put("/logo")
def put_theme_logo(
    file: UploadFile = File(...),
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
) -> None:
    content = file.file.read(MAX_LOGO_BYTES + 1)
    if len(content) > MAX_LOGO_BYTES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Logo must be 2 MB or smaller")
    if file.content_type not in ALLOWED_LOGO_MIME_TYPES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Logo must be PNG, JPEG or WebP")

    file_store = get_default_file_store()
    file_store.delete_file(THEME_LOGO_FILE_ID, error_on_missing=False)
    file_store.save_file(
        content=io.BytesIO(content),
        display_name="theme_logo",
        file_origin=FileOrigin.OTHER,
        file_type=file.content_type,
        file_id=THEME_LOGO_FILE_ID,
    )
