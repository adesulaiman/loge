# Chat documents

> A Markdown document that the agent and its owner edit in turn. The agent
> writes it with the `document` tool. The owner edits it in a side panel. Every
> save appends a version.

**Verified against:** `a6a46f9e5` (2026-10-22)
**Domain:** core-loop
**Edition:** CE
**Owns:**
`backend/onyx/db/chat_document.py`, `backend/onyx/db/chat_document_comment.py`,
`backend/onyx/tools/tool_implementations/document/document_tool.py`,
`backend/onyx/server/features/documents/` (`api.py`, `models.py`, `pdf_export.py`, `assist.py`),
`web/src/lib/documents/` (`hooks.ts`, `svc.ts`, `store.ts`, `types.ts`),
`web/src/sections/document-panel/`

---

## 1. What the user experiences

The user asks the BA Assistant agent for a document, for example a requirements
document built from the knowledge base. The agent searches with `internal_search`,
then calls the `document` tool. A card appears in the chat and the document opens
in the right panel. The user can edit the text, see a preview with Mermaid
diagrams, open the version history, restore a version, and export to Markdown,
Word or PDF. When the user asks for a change, the agent reads the latest version
first, so it keeps the user's edits.

## 2. Surfaces

- Chat: a document card (`DocumentToolRenderer`) for each `document` tool call.
- Right panel in `AppPage.tsx`: `DocumentPanel` (editor, preview, history, export).
- REST API under `/api/documents`.

## 3. Data model

- `chat_document`: owner (`user_id`), title, `current_version`, `deleted`.
  `chat_session_id` has no foreign key, so the document outlives the chat.
- `chat_document_version`: primary key `(document_id, version)`, `content_md`,
  `author` (`user` or `agent`), `summary`.
- A save never edits a version. It appends one and moves `current_version`.
- `chat_document_comment`: a thread root has `parent_id` null and stores the anchor as
  `quote`, `prefix` and `suffix` text. Replies point to the root. `author` is `user` or `ai`.
  `resolved` hides the highlight style, not the thread.

## 4. How it works

**Tool.** One tool, `action` = `create`, `read`, `replace` or `patch`. `patch`
replaces one exact piece of text and fails if it matches zero or many places. The
tool packets are `document_tool_start` and `document_tool_final`. Persisted tool
calls rebuild these packets in `session_loading.create_document_tool_packets`.
A persona must have the tool attached. The row is seeded by an Alembic migration.

**API (owner only).** `GET /`, `GET /{id}?version=`, `PUT /{id}`,
`GET /{id}/versions`, `POST /{id}/restore/{version}`, `DELETE /{id}`,
`GET /{id}/export?format=md|docx|pdf`. DOCX reuses `markdown_to_docx_bytes` from the
Craft export. PDF uses reportlab.

**AI on a selection.** The user selects text in the panel. A bubble menu offers
four ways to ask. "AI comment" saves a thread and an AI reply (`POST /comments`,
`/comments/{id}/replies`). "Continue" and "Rewrite" stream text from
`POST /{id}/ai/stream` with `mode` `continue`, `rewrite` or `instruct` (NDJSON,
`{"delta"}` or `{"error"}`). `instruct` takes a free command typed in the menu and
needs a non-empty `instruction`. The stream saves nothing.
The panel shows the text in a tray. Accept inserts it (for `instruct`: replace the
selection or insert below it), and autosave makes a version.
`assist.py` calls the default LLM with `LLMFlow.DOCUMENT_ASSIST`. With the knowledge
switch on, it runs `search_pipeline` for up to 6 chunks and numbers them `[n]`.

**Panel.** Tiptap edits Markdown. Autosave runs 1.5 s after the last edit. When the
agent saves, the card bumps `agentRevision` in the store and the panel reloads.

## 5. Contracts and invariants

- Writers send `base_version`. `save_version` locks the row and raises
  `DocumentVersionConflictError` when it differs from `current_version`.
- The API answers 409 on a conflict. The tool tells the model to `read` and retry.
- The panel never replaces unsaved user edits. It shows a conflict banner instead.
- Restore appends the old content as a new version.
- Comment anchors are text, never offsets. `commentAnchors.ts` finds the quote again on
  every change with `locateQuote` and draws a decoration. The Markdown never holds a
  comment. If the quote is gone, the thread stays in the list as detached.
- The AI endpoints and the comment endpoints are owner only, like the rest.

## 6. Relationships

- [[tools-framework]]: registration of `DocumentTool`.
- [[streaming-protocol]]: the two document packets.
- [[chat-persistence]] and `session_loading.py`: reload of the card.
- [[internal-search]]: the agent searches first, then writes.

## 7. Blast radius

A new document packet type touches `streaming_models.py`, `streamingModels.ts`,
`renderMessageComponent.tsx` and the packet helpers. A change to the version rules
touches `chat_document.py`, the tool and the panel.

## 8. How to verify a change

Create a document through the agent, edit it in the panel, ask the agent for a
change, and check that the new version keeps the edit. Export all three formats.
Reload the chat and check that the card still shows.

## 9. Footguns

- A comment on text that the user rewrites loses its highlight. The thread stays.
- Mobile does not render the document packets yet.
- Tiptap converts Markdown both ways. Complex tables and raw HTML may change on
  the first save.
- Mermaid is rendered in the browser with `securityLevel: "strict"`. Exports keep
  Mermaid as a code block.
- No sharing yet: only the owner can read a document.
