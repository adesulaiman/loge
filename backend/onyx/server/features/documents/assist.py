"""AI help for a selected block of a document: comment, continue or rewrite."""

from collections.abc import Iterator
from typing import Literal

from sqlalchemy.orm import Session

from onyx.context.search.models import ChunkSearchRequest
from onyx.context.search.pipeline import search_pipeline
from onyx.db.models import ChatDocumentComment, User
from onyx.db.search_settings import get_current_search_settings
from onyx.document_index.factory import get_default_document_index
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.llm.factory import get_default_llm
from onyx.llm.interfaces import LLM, GenerationContext
from onyx.llm.models import (
    GenerationErrorEvent,
    GenerationOptions,
    GenerationRequest,
    ReasoningEffort,
    TextDeltaEvent,
    UserMessage,
)
from onyx.prompts.document_assist import (
    DOCUMENT_ASSIST_SYSTEM_PROMPT,
    DOCUMENT_COMMENT_INSTRUCTION,
    DOCUMENT_CONTINUE_INSTRUCTION,
    DOCUMENT_INSTRUCT_INSTRUCTION,
    DOCUMENT_REWRITE_INSTRUCTION,
)
from onyx.tracing.flows import LLMFlow
from onyx.utils.logger import setup_logger

logger = setup_logger()

AssistMode = Literal["continue", "rewrite", "instruct"]

MAX_SELECTION_CHARS = 6000
MAX_CONTEXT_CHARS = 3000
MAX_INSTRUCTION_CHARS = 1000
MAX_THREAD_CHARS = 4000
SOURCE_LIMIT = 6
SOURCE_CHARS = 1200
MAX_OUTPUT_TOKENS = 3000
# Some models still think before they answer, and the thinking uses this budget.
MAX_COMMENT_TOKENS = 1500

_CONTEXT = GenerationContext(flow=LLMFlow.DOCUMENT_ASSIST)


def search_knowledge(
    query: str, user: User, db_session: Session
) -> tuple[str, list[str]]:
    """Return numbered source text for the prompt and the matching source names."""
    document_index = get_default_document_index(
        get_current_search_settings(db_session), None
    )
    chunks = search_pipeline(
        chunk_search_request=ChunkSearchRequest(
            query=query[:500].strip(), limit=SOURCE_LIMIT
        ),
        document_index=document_index,
        user=user,
        persona_search_info=None,
        db_session=db_session,
    )
    lines: list[str] = []
    names: list[str] = []
    for number, chunk in enumerate(chunks[:SOURCE_LIMIT], start=1):
        lines.append(
            f"[{number}] {chunk.semantic_identifier}\n{chunk.content[:SOURCE_CHARS]}"
        )
        names.append(chunk.semantic_identifier)
    return "\n\n".join(lines), names


def _get_llm() -> LLM:
    try:
        return get_default_llm()
    except ValueError as e:
        raise OnyxError(OnyxErrorCode.SERVICE_UNAVAILABLE, str(e)) from e


def _request(prompt: str, max_tokens: int | None) -> GenerationRequest:
    return GenerationRequest(
        system_prompt=DOCUMENT_ASSIST_SYSTEM_PROMPT,
        messages=[UserMessage(content=prompt)],
        options=GenerationOptions(
            reasoning_effort=ReasoningEffort.OFF, max_tokens=max_tokens
        ),
    )


def _compose(
    instruction: str,
    title: str,
    selection: str,
    before: str,
    after: str,
    user_instruction: str | None,
    sources: str,
    thread: str = "",
) -> str:
    parts = [
        instruction,
        f"Document title: {title}",
        f"Text before the selection:\n{before[-MAX_CONTEXT_CHARS:]}",
        f"Selected text:\n{selection[:MAX_SELECTION_CHARS]}",
        f"Text after the selection:\n{after[:MAX_CONTEXT_CHARS]}",
    ]
    if thread:
        parts.append(f"Comment thread so far:\n{thread[-MAX_THREAD_CHARS:]}")
    if user_instruction and user_instruction.strip():
        parts.append(
            f"User instruction:\n{user_instruction.strip()[:MAX_INSTRUCTION_CHARS]}"
        )
    if sources:
        parts.append(f"Sources:\n{sources}")
    return "\n\n".join(parts)


def format_thread(comments: list[ChatDocumentComment]) -> str:
    return "\n".join(f"{c.author}: {c.body}" for c in comments)


def generate_comment(
    title: str,
    selection: str,
    before: str,
    after: str,
    user_instruction: str | None,
    sources: str,
    thread: str = "",
) -> str:
    prompt = _compose(
        DOCUMENT_COMMENT_INSTRUCTION,
        title,
        selection,
        before,
        after,
        user_instruction,
        sources,
        thread,
    )
    message = _get_llm().invoke(_request(prompt, MAX_COMMENT_TOKENS), _CONTEXT)
    answer = message.text.strip()
    if not answer:
        raise OnyxError(
            OnyxErrorCode.LLM_PROVIDER_ERROR,
            "The model returned no comment. Try again.",
        )
    return answer


def stream_assist(
    mode: AssistMode,
    title: str,
    selection: str,
    before: str,
    after: str,
    user_instruction: str | None,
    sources: str,
) -> Iterator[str]:
    instruction = {
        "continue": DOCUMENT_CONTINUE_INSTRUCTION,
        "rewrite": DOCUMENT_REWRITE_INSTRUCTION,
        "instruct": DOCUMENT_INSTRUCT_INSTRUCTION,
    }[mode]
    if mode == "instruct" and not (user_instruction or "").strip():
        raise OnyxError(OnyxErrorCode.INVALID_INPUT, "Write an instruction for the AI")
    prompt = _compose(
        instruction, title, selection, before, after, user_instruction, sources
    )
    for event in _get_llm().stream(_request(prompt, MAX_OUTPUT_TOKENS), _CONTEXT):
        if isinstance(event, TextDeltaEvent):
            if event.text:
                yield event.text
        elif isinstance(event, GenerationErrorEvent):
            raise OnyxError(OnyxErrorCode.LLM_PROVIDER_ERROR, event.error_message)
