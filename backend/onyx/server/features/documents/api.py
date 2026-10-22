import json
import re
from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from onyx.auth.permissions import require_permission
from onyx.db.chat_document import (
    AUTHOR_USER as VERSION_AUTHOR_USER,
)
from onyx.db.chat_document import (
    DocumentNotFoundError,
    DocumentVersionConflictError,
    delete_document,
    get_document,
    get_version,
    list_documents,
    list_versions,
    save_version,
)
from onyx.db.chat_document_comment import (
    AUTHOR_AI,
    AUTHOR_USER,
    add_comment,
    delete_comment,
    get_comment,
    list_comments,
    set_resolved,
)
from onyx.db.engine.sql_engine import get_session
from onyx.db.enums import Permission
from onyx.db.models import User
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.server.features.build.session.md_to_docx import markdown_to_docx_bytes
from onyx.server.features.documents.assist import (
    format_thread,
    generate_comment,
    search_knowledge,
    stream_assist,
)
from onyx.server.features.documents.models import (
    AssistRequest,
    CommentCreate,
    CommentResolve,
    CommentSnapshot,
    DocumentSnapshot,
    DocumentSummary,
    DocumentUpdate,
    ReplyCreate,
    VersionSummary,
)
from onyx.server.features.documents.pdf_export import markdown_to_pdf_bytes

router = APIRouter(prefix="/documents")

_NO_SOURCES = ""

_EXPORT_TYPES = {
    "md": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


def _not_found() -> OnyxError:
    return OnyxError(OnyxErrorCode.NOT_FOUND, "Document not found")


@router.get("")
def list_my_documents(
    chat_session_id: UUID | None = None,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[DocumentSummary]:
    return [
        DocumentSummary.from_model(d)
        for d in list_documents(db_session, user.id, chat_session_id)
    ]


@router.get("/{document_id}")
def get_my_document(
    document_id: UUID,
    version: int | None = None,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> DocumentSnapshot:
    try:
        document, current = get_document(db_session, document_id, user.id)
        chosen = (
            current
            if version is None
            else get_version(db_session, document.id, version)
        )
    except DocumentNotFoundError:
        raise _not_found()
    return DocumentSnapshot.from_models(document, chosen)


@router.put("/{document_id}")
def update_my_document(
    document_id: UUID,
    body: DocumentUpdate,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> DocumentSnapshot:
    try:
        document, version = save_version(
            db_session,
            document_id=document_id,
            user_id=user.id,
            content_md=body.content_md,
            base_version=body.base_version,
            author=VERSION_AUTHOR_USER,
            title=body.title,
            summary=body.summary,
        )
    except DocumentNotFoundError:
        raise _not_found()
    except DocumentVersionConflictError as e:
        raise OnyxError(
            OnyxErrorCode.CONFLICT,
            f"Document changed. Latest version is {e.current_version}.",
        )
    return DocumentSnapshot.from_models(document, version)


@router.get("/{document_id}/versions")
def list_document_versions(
    document_id: UUID,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[VersionSummary]:
    try:
        return [
            VersionSummary.from_model(v)
            for v in list_versions(db_session, document_id, user.id)
        ]
    except DocumentNotFoundError:
        raise _not_found()


@router.post("/{document_id}/restore/{version}")
def restore_document_version(
    document_id: UUID,
    version: int,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> DocumentSnapshot:
    """Restore appends the old content as a new version, so history stays intact."""
    try:
        document, current = get_document(db_session, document_id, user.id)
        old = get_version(db_session, document.id, version)
        document, saved = save_version(
            db_session,
            document_id=document.id,
            user_id=user.id,
            content_md=old.content_md,
            base_version=current.version,
            author=VERSION_AUTHOR_USER,
            summary=f"Restored version {version}",
        )
    except DocumentNotFoundError:
        raise _not_found()
    return DocumentSnapshot.from_models(document, saved)


@router.delete("/{document_id}")
def delete_my_document(
    document_id: UUID,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        delete_document(db_session, document_id, user.id)
    except DocumentNotFoundError:
        raise _not_found()


@router.get("/{document_id}/export")
def export_document(
    document_id: UUID,
    format: str = "md",
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> Response:
    if format not in _EXPORT_TYPES:
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "format must be md, docx or pdf")
    try:
        document, current = get_document(db_session, document_id, user.id)
    except DocumentNotFoundError:
        raise _not_found()
    content = current.content_md
    body: bytes
    if format == "docx":
        body = markdown_to_docx_bytes(content)
    elif format == "pdf":
        body = markdown_to_pdf_bytes(document.title, content)
    else:
        body = content.encode("utf-8")
    stem = re.sub(r"[^\w\-. ]+", "_", document.title).strip() or "document"
    return Response(
        content=body,
        media_type=_EXPORT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{stem}.{format}"'},
    )


def _sources(use_knowledge: bool, query: str, user: User, db_session: Session) -> str:
    if not use_knowledge or not query.strip():
        return _NO_SOURCES
    sources, _ = search_knowledge(query, user, db_session)
    return sources


@router.get("/{document_id}/comments")
def list_document_comments(
    document_id: UUID,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[CommentSnapshot]:
    try:
        return [
            CommentSnapshot.from_model(c)
            for c in list_comments(db_session, document_id, user.id)
        ]
    except DocumentNotFoundError:
        raise _not_found()


@router.post("/{document_id}/comments")
def create_document_comment(
    document_id: UUID,
    body: CommentCreate,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[CommentSnapshot]:
    """Start a thread on quoted text. Returns the new comments (user, then AI)."""
    try:
        document, _ = get_document(db_session, document_id, user.id)
        created = []
        root = add_comment(
            db_session,
            document_id,
            user.id,
            AUTHOR_USER,
            body.body or body.instruction or "",
            quote=body.selection,
            prefix=body.prefix,
            suffix=body.suffix,
        )
        created.append(root)
        if body.ask_ai:
            sources = _sources(
                body.use_knowledge,
                f"{body.selection} {body.instruction or body.body}",
                user,
                db_session,
            )
            answer = generate_comment(
                document.title,
                body.selection,
                body.before,
                body.after,
                body.instruction or body.body,
                sources,
            )
            created.append(
                add_comment(
                    db_session,
                    document_id,
                    user.id,
                    AUTHOR_AI,
                    answer,
                    parent_id=root.id,
                )
            )
    except DocumentNotFoundError:
        raise _not_found()
    return [CommentSnapshot.from_model(c) for c in created]


@router.post("/{document_id}/comments/{comment_id}/replies")
def reply_to_comment(
    document_id: UUID,
    comment_id: UUID,
    body: ReplyCreate,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[CommentSnapshot]:
    try:
        document, current = get_document(db_session, document_id, user.id)
        root = get_comment(db_session, document_id, comment_id, user.id)
        if root.parent_id is not None:
            raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Reply to the first comment")
        created = []
        if body.body.strip():
            created.append(
                add_comment(
                    db_session,
                    document_id,
                    user.id,
                    AUTHOR_USER,
                    body.body,
                    parent_id=root.id,
                )
            )
        if body.ask_ai:
            thread = [
                c
                for c in list_comments(db_session, document_id, user.id)
                if c.id == root.id or c.parent_id == root.id
            ]
            sources = _sources(
                body.use_knowledge, f"{root.quote} {body.body}", user, db_session
            )
            answer = generate_comment(
                document.title,
                root.quote,
                "",
                "",
                body.body or None,
                sources,
                thread=format_thread(thread),
            )
            created.append(
                add_comment(
                    db_session,
                    document_id,
                    user.id,
                    AUTHOR_AI,
                    answer,
                    parent_id=root.id,
                )
            )
    except DocumentNotFoundError:
        raise _not_found()
    return [CommentSnapshot.from_model(c) for c in created]


@router.patch("/{document_id}/comments/{comment_id}")
def resolve_comment(
    document_id: UUID,
    comment_id: UUID,
    body: CommentResolve,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> CommentSnapshot:
    try:
        return CommentSnapshot.from_model(
            set_resolved(db_session, document_id, comment_id, user.id, body.resolved)
        )
    except DocumentNotFoundError:
        raise _not_found()


@router.delete("/{document_id}/comments/{comment_id}")
def remove_comment(
    document_id: UUID,
    comment_id: UUID,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        delete_comment(db_session, document_id, comment_id, user.id)
    except DocumentNotFoundError:
        raise _not_found()


@router.post("/{document_id}/ai/stream")
def stream_document_assist(
    document_id: UUID,
    body: AssistRequest,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream a continuation or rewrite as NDJSON lines. Nothing is saved."""
    try:
        document, _ = get_document(db_session, document_id, user.id)
    except DocumentNotFoundError:
        raise _not_found()
    sources = _sources(
        body.use_knowledge,
        f"{body.selection} {body.instruction or ''}",
        user,
        db_session,
    )
    title = document.title

    def lines() -> Iterator[str]:
        try:
            for delta in stream_assist(
                body.mode,
                title,
                body.selection,
                body.before,
                body.after,
                body.instruction,
                sources,
            ):
                yield json.dumps({"delta": delta}) + "\n"
        except OnyxError as e:
            yield json.dumps({"error": e.detail}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")
