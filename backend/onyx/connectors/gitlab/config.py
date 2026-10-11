from typing import Annotated, Any, Literal

from pydantic import field_validator

from onyx.configs.app_configs import INDEX_BATCH_SIZE
from onyx.connectors.connector_config import ConnectorConfig
from onyx.connectors.cross_connector_utils.git_indexable_files import (
    BRANCH_MODE_SINGLE,
)
from onyx.connectors.field_policy import (
    FieldClass,
    FieldPolicy,
    ScopeOpaque,
    ScopeToggle,
)

# Merge request and issue document ids are web URLs that contain the project path.
_PROJECT_PATH = FieldPolicy(FieldClass.IDENTITY)
_DOCUMENT_TYPE_TOGGLE = FieldPolicy(
    FieldClass.SCOPE, scope=ScopeToggle(widens_when=True)
)


class GitlabConnectorConfig(ConnectorConfig):
    project_owner: Annotated[str, _PROJECT_PATH]
    project_name: Annotated[str, _PROJECT_PATH]
    batch_size: Annotated[int, FieldPolicy(FieldClass.COSMETIC)] = INDEX_BATCH_SIZE
    state_filter: Annotated[str, FieldPolicy(FieldClass.SCOPE, scope=ScopeOpaque())] = (
        "all"
    )
    include_mrs: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = False
    include_issues: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = False
    include_code_files: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = True
    branch_mode: Annotated[
        Literal["single", "all"], FieldPolicy(FieldClass.IDENTITY)
    ] = BRANCH_MODE_SINGLE
    branch: Annotated[str | None, FieldPolicy(FieldClass.IDENTITY)] = None

    @field_validator("branch", mode="before")
    @classmethod
    def _strip_blank_to_none(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("branch_mode", mode="before")
    @classmethod
    def _normalize_branch_mode(cls, value: Any) -> Any:
        if value is None or value == "":
            return BRANCH_MODE_SINGLE
        if isinstance(value, str):
            return value.strip().lower()
        return value
