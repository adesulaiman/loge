from uuid import UUID

from pydantic import BaseModel, Field

from onyx.db.models import UserGroup as UserGroupModel
from onyx.server.documents.models import ConnectorCredentialPairDescriptor
from onyx.server.features.document_set.models import DocumentSet
from onyx.server.features.persona.models import PersonaSnapshot
from onyx.server.manage.models import UserInfo, UserPreferences


class GroupSnapshot(BaseModel):
    """Group as the admin Groups page reads it (web `UserGroup` type)."""

    id: int
    name: str
    users: list[UserInfo]
    manager_ids: list[str]
    cc_pairs: list[ConnectorCredentialPairDescriptor]
    document_sets: list[DocumentSet]
    personas: list[PersonaSnapshot]
    is_up_to_date: bool
    is_up_for_deletion: bool
    is_default: bool
    incognito_enabled: bool
    permissions: dict[str, bool] = Field(default_factory=dict)

    @classmethod
    def from_model(
        cls,
        group: UserGroupModel,
        *,
        mask_credential_prefix: bool,
        permissions: dict[str, bool],
    ) -> "GroupSnapshot":
        return cls(
            id=group.id,
            name=group.name,
            users=[
                UserInfo(
                    id=str(user.id),
                    email=user.email,
                    is_active=user.is_active,
                    is_superuser=user.is_superuser,
                    is_verified=user.is_verified,
                    account_type=user.account_type,
                    preferences=UserPreferences(
                        default_model=user.default_model,
                        chosen_assistants=user.chosen_assistants,
                    ),
                )
                for user in group.users
            ],
            manager_ids=[
                str(rel.user_id)
                for rel in group.user_group_relationships
                if rel.is_manager and rel.user_id is not None
            ],
            cc_pairs=[],
            document_sets=[
                DocumentSet.from_model(
                    ds, mask_credential_prefix=mask_credential_prefix
                )
                for ds in group.document_sets
            ],
            personas=[
                PersonaSnapshot.from_model(p) for p in group.personas if not p.deleted
            ],
            is_up_to_date=group.is_up_to_date,
            is_up_for_deletion=group.is_up_for_deletion,
            is_default=group.is_default,
            incognito_enabled=group.incognito_enabled,
            permissions=permissions,
        )


class MinimalGroup(BaseModel):
    id: int
    name: str
    is_default: bool


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    user_ids: list[UUID] = Field(default_factory=list)
    # Accepted for web compatibility; connector links are not managed here.
    cc_pair_ids: list[int] = Field(default_factory=list)


class GroupRename(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=100)


class GroupMembersUpdate(BaseModel):
    user_ids: list[UUID]
    cc_pair_ids: list[int] | None = None


class AddUsersRequest(BaseModel):
    user_ids: list[UUID]


class AgentsUpdate(BaseModel):
    added_agent_ids: list[int] = Field(default_factory=list)
    removed_agent_ids: list[int] = Field(default_factory=list)


class DocumentSetsUpdate(BaseModel):
    added_document_set_ids: list[int] = Field(default_factory=list)
    removed_document_set_ids: list[int] = Field(default_factory=list)
