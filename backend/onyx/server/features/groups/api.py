from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from onyx.auth.permission_projection import user_group_permissions
from onyx.auth.permissions import has_global_permission, require_permission
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.group_management import (
    add_members,
    create_group,
    delete_group,
    fetch_groups,
    get_group,
    rename_group,
    update_group_agents,
    update_group_document_sets,
    update_members,
)
from onyx.db.models import User, UserGroup
from onyx.server.features.groups.models import (
    AddUsersRequest,
    AgentsUpdate,
    DocumentSetsUpdate,
    GroupCreate,
    GroupMembersUpdate,
    GroupRename,
    GroupSnapshot,
    MinimalGroup,
)
from onyx.server.security.store import get_security_settings

router = APIRouter(prefix="/manage")


def _snapshot(group_id: int, user: User, db_session: Session) -> GroupSnapshot:
    return _to_snapshot(get_group(db_session, group_id), user)


def _to_snapshot(group: UserGroup, user: User) -> GroupSnapshot:
    return GroupSnapshot.from_model(
        group,
        mask_credential_prefix=get_security_settings().mask_credential_prefix,
        permissions=user_group_permissions(
            can_manage=True,
            is_user_groups_admin=True,
            is_full_admin=has_global_permission(
                user, Permission.FULL_ADMIN_PANEL_ACCESS
            ),
            is_default=group.is_default,
        ),
    )


@router.get("/groups")
def list_groups(
    include_default: bool = False,
    user: User = Depends(require_permission(Permission.READ_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> list[GroupSnapshot]:
    return [_to_snapshot(g, user) for g in fetch_groups(db_session, include_default)]


@router.get("/groups/minimal")
def list_minimal_groups(
    _: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[MinimalGroup]:
    return [
        MinimalGroup(id=g.id, name=g.name, is_default=g.is_default)
        for g in fetch_groups(db_session, include_default=True)
    ]


@router.post("/groups")
def create_group_endpoint(
    body: GroupCreate,
    user: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> GroupSnapshot:
    group_id = create_group(db_session, body.name, body.user_ids)
    return _snapshot(group_id, user, db_session)


@router.patch("/groups/rename")
def rename_group_endpoint(
    body: GroupRename,
    _: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> None:
    rename_group(db_session, body.id, body.name)


@router.patch("/groups/{group_id}")
def update_members_endpoint(
    group_id: int,
    body: GroupMembersUpdate,
    user: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> GroupSnapshot:
    update_members(db_session, group_id, body.user_ids)
    return _snapshot(group_id, user, db_session)


@router.post("/groups/{group_id}/add-users")
def add_users_endpoint(
    group_id: int,
    body: AddUsersRequest,
    user: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> GroupSnapshot:
    add_members(db_session, group_id, body.user_ids)
    return _snapshot(group_id, user, db_session)


@router.delete("/groups/{group_id}")
def delete_group_endpoint(
    group_id: int,
    _: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> None:
    delete_group(db_session, group_id)


@router.patch("/groups/{group_id}/agents")
def update_agents_endpoint(
    group_id: int,
    body: AgentsUpdate,
    _: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> None:
    update_group_agents(
        db_session, group_id, body.added_agent_ids, body.removed_agent_ids
    )


@router.patch("/groups/{group_id}/document-sets")
def update_document_sets_endpoint(
    group_id: int,
    body: DocumentSetsUpdate,
    _: User = Depends(require_permission(Permission.MANAGE_USER_GROUPS)),
    db_session: Session = Depends(get_session),
) -> None:
    update_group_document_sets(
        db_session,
        group_id,
        body.added_document_set_ids,
        body.removed_document_set_ids,
    )
