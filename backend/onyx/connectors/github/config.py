from typing import Annotated, Any, Literal

from pydantic import field_validator

from onyx.connectors.connector_config import ConnectorConfig
from onyx.connectors.cross_connector_utils.git_indexable_files import (
    BRANCH_MODE_SINGLE,
)
from onyx.connectors.field_policy import (
    FieldClass,
    FieldPolicy,
    ScopeInclude,
    ScopeOpaque,
    ScopeToggle,
)

_DOCUMENT_TYPE_TOGGLE = FieldPolicy(
    FieldClass.SCOPE, scope=ScopeToggle(widens_when=True)
)


class GithubConnectorConfig(ConnectorConfig):
    repo_owner: Annotated[str, FieldPolicy(FieldClass.IDENTITY)]
    repositories: Annotated[
        str | None,
        FieldPolicy(FieldClass.SCOPE, scope=ScopeInclude(empty_means_all=True)),
    ] = None
    state_filter: Annotated[str, FieldPolicy(FieldClass.SCOPE, scope=ScopeOpaque())] = (
        "all"
    )
    include_prs: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = False
    include_issues: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = False
    include_files: Annotated[bool, _DOCUMENT_TYPE_TOGGLE] = True
    # single = one branch tip (branch blank → repo default). all = every tip.
    branch_mode: Annotated[
        Literal["single", "all"], FieldPolicy(FieldClass.IDENTITY)
    ] = BRANCH_MODE_SINGLE
    # Used when branch_mode is single. File document ids contain the branch.
    branch: Annotated[str | None, FieldPolicy(FieldClass.IDENTITY)] = None

    # A blank value means every repository or the default branch, as in the
    # connector.
    @field_validator("repositories", "branch", mode="before")
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
