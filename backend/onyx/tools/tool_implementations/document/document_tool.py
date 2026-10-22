"""Create, read and edit a Markdown document the user can open in a side panel.

The agent and the user edit in turn. Every write appends a version, and
replace/patch must name the version they were based on. A stale base_version
is refused with the current version, so the agent reads the user's edits first.
"""

import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import override

from onyx.chat.emitter import Emitter
from onyx.db.chat_document import (
    AUTHOR_AGENT,
    DocumentNotFoundError,
    DocumentPatchError,
    DocumentVersionConflictError,
    create_document,
    get_document,
    patch_content,
    save_version,
)
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.llm.models import ToolDefinition
from onyx.server.query_and_chat.placement import Placement
from onyx.server.query_and_chat.streaming_models import (
    DocumentToolFinal,
    DocumentToolStart,
    Packet,
)
from onyx.tools.interface import Tool
from onyx.tools.models import ToolCallException, ToolResponse

ACTION_FIELD = "action"
ACTIONS = ("create", "read", "replace", "patch")


class DocumentToolOverrideKwargs(BaseModel):
    pass


class DocumentTool(Tool[DocumentToolOverrideKwargs | None]):
    NAME = "document"
    DISPLAY_NAME = "Document"
    DESCRIPTION = (
        "Create, read and edit a Markdown document that the user can open and edit "
        "in a side panel. Use it for requirements documents, analysis reports and "
        "similar written deliverables instead of pasting them in the chat."
    )

    def __init__(
        self,
        tool_id: int,
        emitter: Emitter,
        user_id: UUID,
        chat_session_id: UUID | None,
    ) -> None:
        super().__init__(emitter=emitter)
        self._id = tool_id
        self._user_id = user_id
        self._chat_session_id = chat_session_id

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    def tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    ACTION_FIELD: {
                        "type": "string",
                        "enum": list(ACTIONS),
                        "description": (
                            "create: new document (needs title, content_md). "
                            "read: return the latest content (needs doc_id). "
                            "replace: write the whole content (needs doc_id, "
                            "base_version, content_md). "
                            "patch: replace one exact piece of text (needs doc_id, "
                            "base_version, old_text, new_text)."
                        ),
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Id returned by create. Not used by create.",
                    },
                    "title": {"type": "string", "description": "Document title."},
                    "content_md": {
                        "type": "string",
                        "description": (
                            "Full document content in Markdown. Use headings, "
                            "tables and ```mermaid blocks for diagrams. Cite "
                            "sources from internal_search as [n]."
                        ),
                    },
                    "base_version": {
                        "type": "integer",
                        "description": (
                            "The version you last read or wrote. Required for "
                            "replace and patch."
                        ),
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace. Must match once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Text that replaces old_text.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Short note on what changed in this version.",
                    },
                },
                "required": [ACTION_FIELD],
            },
        )

    @override
    def emit_start(self, placement: Placement) -> None:
        self.emitter.emit(Packet(placement=placement, obj=DocumentToolStart()))

    def _require(self, llm_kwargs: dict[str, Any], *fields: str) -> None:
        missing = [f for f in fields if llm_kwargs.get(f) in (None, "")]
        if missing:
            raise ToolCallException(
                message=f"document tool missing parameters: {missing}",
                llm_facing_message=(
                    f"The document tool needs these parameters for this action: "
                    f"{', '.join(missing)}."
                ),
            )

    def _doc_id(self, llm_kwargs: dict[str, Any]) -> UUID:
        try:
            return UUID(str(llm_kwargs["doc_id"]))
        except ValueError as e:
            raise ToolCallException(
                message="invalid doc_id",
                llm_facing_message="doc_id is not valid. Use the id returned by create.",
            ) from e

    def _finish(
        self,
        placement: Placement,
        action: str,
        doc_id: UUID,
        version: int,
        title: str,
        extra: dict[str, Any] | None = None,
    ) -> ToolResponse:
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=DocumentToolFinal(
                    action=action, doc_id=str(doc_id), version=version, title=title
                ),
            )
        )
        payload: dict[str, Any] = {
            "status": "ok",
            "doc_id": str(doc_id),
            "version": version,
            "title": title,
        }
        if extra:
            payload.update(extra)
        return ToolResponse(rich_response=None, llm_facing_response=json.dumps(payload))

    @override
    def run(
        self,
        placement: Placement,
        override_kwargs: DocumentToolOverrideKwargs | None,  # noqa: ARG002
        **llm_kwargs: Any,
    ) -> ToolResponse:
        action = llm_kwargs.get(ACTION_FIELD)
        if action not in ACTIONS:
            raise ToolCallException(
                message=f"unknown document action: {action}",
                llm_facing_message=f"action must be one of: {', '.join(ACTIONS)}.",
            )
        try:
            return self._run_action(placement, str(action), llm_kwargs)
        except DocumentNotFoundError as e:
            raise ToolCallException(
                message=f"document not found: {e}",
                llm_facing_message="That document does not exist or was deleted.",
            ) from e
        except DocumentVersionConflictError as e:
            raise ToolCallException(
                message=str(e),
                llm_facing_message=(
                    f"The user changed the document. It is now at version "
                    f"{e.current_version}. Call read, then apply your change to "
                    f"that content with base_version={e.current_version}."
                ),
            ) from e
        except DocumentPatchError as e:
            raise ToolCallException(
                message=str(e),
                llm_facing_message=f"Patch failed: {e}. Call read and retry.",
            ) from e

    def _run_action(
        self, placement: Placement, action: str, llm_kwargs: dict[str, Any]
    ) -> ToolResponse:
        with get_session_with_current_tenant() as db_session:
            if action == "create":
                self._require(llm_kwargs, "title", "content_md")
                document = create_document(
                    db_session,
                    user_id=self._user_id,
                    title=str(llm_kwargs["title"]),
                    content_md=str(llm_kwargs["content_md"]),
                    chat_session_id=self._chat_session_id,
                    author=AUTHOR_AGENT,
                )
                return self._finish(placement, action, document.id, 1, document.title)

            self._require(llm_kwargs, "doc_id")
            doc_id = self._doc_id(llm_kwargs)

            if action == "read":
                document, version = get_document(db_session, doc_id, self._user_id)
                return self._finish(
                    placement,
                    action,
                    document.id,
                    version.version,
                    document.title,
                    extra={"content_md": version.content_md, "author": version.author},
                )

            self._require(llm_kwargs, "base_version")
            base_version = int(llm_kwargs["base_version"])
            if action == "replace":
                self._require(llm_kwargs, "content_md")
                new_content = str(llm_kwargs["content_md"])
            else:
                self._require(llm_kwargs, "old_text")
                document, current = get_document(db_session, doc_id, self._user_id)
                if current.version != base_version:
                    raise DocumentVersionConflictError(current.version)
                new_content = patch_content(
                    current.content_md,
                    str(llm_kwargs["old_text"]),
                    str(llm_kwargs.get("new_text", "")),
                )
            document, saved = save_version(
                db_session,
                document_id=doc_id,
                user_id=self._user_id,
                content_md=new_content,
                base_version=base_version,
                author=AUTHOR_AGENT,
                title=llm_kwargs.get("title") or None,
                summary=llm_kwargs.get("summary") or None,
            )
            return self._finish(
                placement, action, document.id, saved.version, document.title
            )
