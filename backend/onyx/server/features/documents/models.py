import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from onyx.db.models import ChatDocument, ChatDocumentComment, ChatDocumentVersion


class DocumentSummary(BaseModel):
    id: UUID
    title: str
    current_version: int
    chat_session_id: UUID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_model(cls, document: ChatDocument) -> "DocumentSummary":
        return cls(
            id=document.id,
            title=document.title,
            current_version=document.current_version,
            chat_session_id=document.chat_session_id,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentSnapshot(DocumentSummary):
    content_md: str
    author: str

    @classmethod
    def from_models(
        cls, document: ChatDocument, version: ChatDocumentVersion
    ) -> "DocumentSnapshot":
        return cls(
            **DocumentSummary.from_model(document).model_dump(),
            content_md=version.content_md,
            author=version.author,
        )


class VersionSummary(BaseModel):
    version: int
    author: str
    summary: str | None
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, version: ChatDocumentVersion) -> "VersionSummary":
        return cls(
            version=version.version,
            author=version.author,
            summary=version.summary,
            created_at=version.created_at,
        )


class DocumentUpdate(BaseModel):
    content_md: str
    base_version: int
    title: str | None = None
    summary: str | None = None


class CommentSnapshot(BaseModel):
    id: UUID
    parent_id: UUID | None
    author: str
    body: str
    quote: str
    prefix: str
    suffix: str
    created_on_version: int
    resolved: bool
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, comment: ChatDocumentComment) -> "CommentSnapshot":
        return cls(
            id=comment.id,
            parent_id=comment.parent_id,
            author=comment.author,
            body=comment.body,
            quote=comment.quote,
            prefix=comment.prefix,
            suffix=comment.suffix,
            created_on_version=comment.created_on_version,
            resolved=comment.resolved,
            created_at=comment.created_at,
        )


class SelectionContext(BaseModel):
    selection: str
    before: str = ""
    after: str = ""
    instruction: str | None = None
    use_knowledge: bool = False


class CommentCreate(SelectionContext):
    """A new thread on a quote. An empty body with ask_ai only asks the AI."""

    prefix: str = ""
    suffix: str = ""
    body: str = ""
    ask_ai: bool = True


class ReplyCreate(BaseModel):
    body: str = ""
    ask_ai: bool = True
    use_knowledge: bool = False


class CommentResolve(BaseModel):
    resolved: bool


class AssistRequest(SelectionContext):
    mode: Literal["continue", "rewrite", "instruct"]
