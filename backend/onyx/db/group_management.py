"""Create, edit and delete user groups.

Default groups (Admin, Basic) keep their name and cannot be deleted. Their
members can still change. Group-to-resource links for connectors are not
managed here.
"""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from onyx.db.enums import PersonaSharePermission
from onyx.db.models import (
    Credential__UserGroup,
    DocumentSet,
    DocumentSet__UserGroup,
    LLMProvider__UserGroup,
    MCPServer__UserGroup,
    Persona,
    Persona__UserGroup,
    Skill__UserGroup,
    TokenRateLimit__UserGroup,
    User,
    User__UserGroup,
    UserGroup,
    UserGroup__ConnectorCredentialPair,
)
from onyx.db.permissions import recompute_user_permissions__no_commit
from onyx.db.user_group import assert_group_config_is_editable
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError


def fetch_groups(db_session: Session, include_default: bool) -> list[UserGroup]:
    stmt = (
        select(UserGroup)
        .where(UserGroup.is_up_for_deletion.is_(False))
        .options(
            selectinload(UserGroup.users),
            selectinload(UserGroup.user_group_relationships),
            selectinload(UserGroup.document_sets),
            selectinload(UserGroup.personas),
        )
        .order_by(UserGroup.name)
    )
    if not include_default:
        stmt = stmt.where(UserGroup.is_default.is_(False))
    return list(db_session.scalars(stmt).all())


def get_group(db_session: Session, group_id: int) -> UserGroup:
    group = db_session.scalar(
        select(UserGroup)
        .where(UserGroup.id == group_id)
        .options(
            selectinload(UserGroup.users),
            selectinload(UserGroup.user_group_relationships),
            selectinload(UserGroup.document_sets),
            selectinload(UserGroup.personas),
        )
    )
    if group is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, f"User group {group_id} not found")
    return group


def _assert_users_exist(db_session: Session, user_ids: Collection[UUID]) -> None:
    if not user_ids:
        return
    found = set(
        db_session.scalars(
            select(User.id).where(User.id.in_(user_ids))  # ty: ignore[no-matching-overload, unresolved-attribute]
        ).all()
    )
    missing = set(user_ids) - found
    if missing:
        raise OnyxError(
            OnyxErrorCode.INVALID_INPUT,
            "Unknown user ids: " + ", ".join(sorted(str(u) for u in missing)),
        )


def _set_members(
    db_session: Session, group_id: int, user_ids: Collection[UUID]
) -> None:
    """Replace the member list. Keeps the manager flag of members who stay."""
    _assert_users_exist(db_session, user_ids)
    wanted = set(user_ids)
    current = set(
        db_session.scalars(
            select(User__UserGroup.user_id).where(
                User__UserGroup.user_group_id == group_id,
                User__UserGroup.user_id.isnot(None),
            )
        ).all()
    )
    removed = current - wanted
    added = wanted - current
    if removed:
        db_session.execute(
            delete(User__UserGroup).where(
                User__UserGroup.user_group_id == group_id,
                User__UserGroup.user_id.in_(removed),
            )
        )
    for user_id in added:
        db_session.add(User__UserGroup(user_group_id=group_id, user_id=user_id))
    db_session.flush()
    changed = [u for u in (removed | added) if u is not None]
    if changed:
        recompute_user_permissions__no_commit(changed, db_session)


def create_group(db_session: Session, name: str, user_ids: Collection[UUID]) -> int:
    group = UserGroup(name=name.strip(), is_up_to_date=True)
    db_session.add(group)
    try:
        db_session.flush()
    except IntegrityError:
        db_session.rollback()
        raise OnyxError(OnyxErrorCode.CONFLICT, f"Group '{name}' already exists")
    _set_members(db_session, group.id, user_ids)
    db_session.commit()
    return group.id


def rename_group(db_session: Session, group_id: int, name: str) -> None:
    group = get_group(db_session, group_id)
    assert_group_config_is_editable(db_session, group_id, "rename")
    group.name = name.strip()
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
        raise OnyxError(OnyxErrorCode.CONFLICT, f"Group '{name}' already exists")


def update_members(
    db_session: Session, group_id: int, user_ids: Collection[UUID]
) -> None:
    get_group(db_session, group_id)
    _set_members(db_session, group_id, user_ids)
    db_session.commit()


def add_members(db_session: Session, group_id: int, user_ids: Collection[UUID]) -> None:
    get_group(db_session, group_id)
    existing = {
        user_id
        for user_id in db_session.scalars(
            select(User__UserGroup.user_id).where(
                User__UserGroup.user_group_id == group_id
            )
        ).all()
        if user_id is not None
    }
    _set_members(db_session, group_id, existing | set(user_ids))
    db_session.commit()


def delete_group(db_session: Session, group_id: int) -> None:
    group = get_group(db_session, group_id)
    if group.is_default:
        raise OnyxError(OnyxErrorCode.CONFLICT, "Cannot delete a default system group.")
    member_ids = [u.id for u in group.users]
    for link in (
        User__UserGroup,
        UserGroup__ConnectorCredentialPair,
        DocumentSet__UserGroup,
        Persona__UserGroup,
        TokenRateLimit__UserGroup,
        LLMProvider__UserGroup,
        Credential__UserGroup,
        Skill__UserGroup,
        MCPServer__UserGroup,
    ):
        db_session.execute(delete(link).where(link.user_group_id == group_id))
    db_session.execute(delete(UserGroup).where(UserGroup.id == group_id))
    db_session.expire_all()
    if member_ids:
        recompute_user_permissions__no_commit(member_ids, db_session)
    db_session.commit()


def update_group_agents(
    db_session: Session, group_id: int, added: Collection[int], removed: Collection[int]
) -> None:
    get_group(db_session, group_id)
    assert_group_config_is_editable(db_session, group_id, "share agents with")
    existing = set(
        db_session.scalars(
            select(Persona__UserGroup.persona_id).where(
                Persona__UserGroup.user_group_id == group_id
            )
        ).all()
    )
    valid = set(
        db_session.scalars(
            select(Persona.id).where(Persona.id.in_(added), Persona.deleted.is_(False))
        ).all()
    )
    for persona_id in valid - existing:
        db_session.add(
            Persona__UserGroup(
                persona_id=persona_id,
                user_group_id=group_id,
                permission=PersonaSharePermission.VIEWER,
            )
        )
    if removed:
        db_session.execute(
            delete(Persona__UserGroup).where(
                Persona__UserGroup.user_group_id == group_id,
                Persona__UserGroup.persona_id.in_(removed),
            )
        )
    db_session.commit()


def update_group_document_sets(
    db_session: Session, group_id: int, added: Collection[int], removed: Collection[int]
) -> None:
    get_group(db_session, group_id)
    assert_group_config_is_editable(db_session, group_id, "share document sets with")
    existing = set(
        db_session.scalars(
            select(DocumentSet__UserGroup.document_set_id).where(
                DocumentSet__UserGroup.user_group_id == group_id
            )
        ).all()
    )
    valid = set(
        db_session.scalars(
            select(DocumentSet.id).where(DocumentSet.id.in_(added))
        ).all()
    )
    for document_set_id in valid - existing:
        db_session.add(
            DocumentSet__UserGroup(
                document_set_id=document_set_id, user_group_id=group_id
            )
        )
    if removed:
        db_session.execute(
            delete(DocumentSet__UserGroup).where(
                DocumentSet__UserGroup.user_group_id == group_id,
                DocumentSet__UserGroup.document_set_id.in_(removed),
            )
        )
    db_session.commit()
