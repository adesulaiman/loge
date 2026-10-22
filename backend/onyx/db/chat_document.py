from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.models import ChatDocument, ChatDocumentVersion

AUTHOR_USER = "user"
AUTHOR_AGENT = "agent"


class DocumentNotFoundError(Exception):
    pass


class DocumentVersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        super().__init__(f"Document is at version {current_version}")
        self.current_version = current_version


class DocumentPatchError(Exception):
    pass


def _get_owned(
    db_session: Session, document_id: UUID, user_id: UUID, for_update: bool = False
) -> ChatDocument:
    stmt = select(ChatDocument).where(
        ChatDocument.id == document_id,
        ChatDocument.user_id == user_id,
        ChatDocument.deleted.is_(False),
    )
    if for_update:
        stmt = stmt.with_for_update()
    document = db_session.scalars(stmt).one_or_none()
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    return document


def get_version(
    db_session: Session, document_id: UUID, version: int
) -> ChatDocumentVersion:
    row = db_session.get(ChatDocumentVersion, (document_id, version))
    if row is None:
        raise DocumentNotFoundError(f"{document_id}@{version}")
    return row


def create_document(
    db_session: Session,
    user_id: UUID,
    title: str,
    content_md: str,
    chat_session_id: UUID | None,
    author: str = AUTHOR_AGENT,
) -> ChatDocument:
    document = ChatDocument(
        id=uuid4(),
        user_id=user_id,
        chat_session_id=chat_session_id,
        title=title,
        current_version=1,
    )
    document.versions.append(
        ChatDocumentVersion(version=1, content_md=content_md, author=author)
    )
    db_session.add(document)
    db_session.commit()
    return document


def list_documents(
    db_session: Session, user_id: UUID, chat_session_id: UUID | None = None
) -> list[ChatDocument]:
    stmt = (
        select(ChatDocument)
        .where(ChatDocument.user_id == user_id, ChatDocument.deleted.is_(False))
        .order_by(ChatDocument.updated_at.desc())
    )
    if chat_session_id is not None:
        stmt = stmt.where(ChatDocument.chat_session_id == chat_session_id)
    return list(db_session.scalars(stmt).all())


def get_document(
    db_session: Session, document_id: UUID, user_id: UUID
) -> tuple[ChatDocument, ChatDocumentVersion]:
    document = _get_owned(db_session, document_id, user_id)
    return document, get_version(db_session, document.id, document.current_version)


def list_versions(
    db_session: Session, document_id: UUID, user_id: UUID
) -> list[ChatDocumentVersion]:
    document = _get_owned(db_session, document_id, user_id)
    return list(reversed(document.versions))


def save_version(
    db_session: Session,
    document_id: UUID,
    user_id: UUID,
    content_md: str,
    base_version: int,
    author: str,
    title: str | None = None,
    summary: str | None = None,
) -> tuple[ChatDocument, ChatDocumentVersion]:
    """Append a version. Raises DocumentVersionConflictError if base_version is stale."""
    document = _get_owned(db_session, document_id, user_id, for_update=True)
    if document.current_version != base_version:
        db_session.rollback()
        raise DocumentVersionConflictError(document.current_version)
    new_version = ChatDocumentVersion(
        document_id=document.id,
        version=document.current_version + 1,
        content_md=content_md,
        author=author,
        summary=summary,
    )
    db_session.add(new_version)
    document.current_version = new_version.version
    if title:
        document.title = title
    db_session.commit()
    return document, new_version


def patch_content(content_md: str, old_text: str, new_text: str) -> str:
    """Replace one exact occurrence of old_text."""
    if not old_text:
        raise DocumentPatchError("old_text must not be empty")
    count = content_md.count(old_text)
    if count == 0:
        raise DocumentPatchError("old_text was not found in the document")
    if count > 1:
        raise DocumentPatchError(
            f"old_text matches {count} places; add more surrounding text"
        )
    return content_md.replace(old_text, new_text, 1)


def delete_document(db_session: Session, document_id: UUID, user_id: UUID) -> None:
    document = _get_owned(db_session, document_id, user_id)
    document.deleted = True
    db_session.commit()
