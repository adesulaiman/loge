from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from onyx.db.chat_document import DocumentNotFoundError, get_document
from onyx.db.models import ChatDocumentComment

AUTHOR_USER = "user"
AUTHOR_AI = "ai"


def list_comments(
    db_session: Session, document_id: UUID, user_id: UUID
) -> list[ChatDocumentComment]:
    """All comments and replies of an owned document, oldest first."""
    get_document(db_session, document_id, user_id)
    return list(
        db_session.scalars(
            select(ChatDocumentComment)
            .where(ChatDocumentComment.document_id == document_id)
            .order_by(ChatDocumentComment.created_at, ChatDocumentComment.id)
        ).all()
    )


def get_comment(
    db_session: Session, document_id: UUID, comment_id: UUID, user_id: UUID
) -> ChatDocumentComment:
    get_document(db_session, document_id, user_id)
    comment = db_session.get(ChatDocumentComment, comment_id)
    if comment is None or comment.document_id != document_id:
        raise DocumentNotFoundError(str(comment_id))
    return comment


def add_comment(
    db_session: Session,
    document_id: UUID,
    user_id: UUID,
    author: str,
    body: str,
    quote: str = "",
    prefix: str = "",
    suffix: str = "",
    parent_id: UUID | None = None,
) -> ChatDocumentComment:
    document, _ = get_document(db_session, document_id, user_id)
    comment = ChatDocumentComment(
        id=uuid4(),
        document_id=document.id,
        parent_id=parent_id,
        author=author,
        body=body,
        quote=quote,
        prefix=prefix,
        suffix=suffix,
        created_on_version=document.current_version,
    )
    db_session.add(comment)
    db_session.commit()
    return comment


def set_resolved(
    db_session: Session,
    document_id: UUID,
    comment_id: UUID,
    user_id: UUID,
    resolved: bool,
) -> ChatDocumentComment:
    comment = get_comment(db_session, document_id, comment_id, user_id)
    comment.resolved = resolved
    db_session.commit()
    return comment


def delete_comment(
    db_session: Session, document_id: UUID, comment_id: UUID, user_id: UUID
) -> None:
    comment = get_comment(db_session, document_id, comment_id, user_id)
    db_session.delete(comment)
    db_session.commit()
