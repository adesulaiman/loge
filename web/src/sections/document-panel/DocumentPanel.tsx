"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "@tiptap/markdown";
import {
  Table,
  TableRow,
  TableHeader,
  TableCell,
} from "@tiptap/extension-table";
import {
  Button,
  InputSwitch,
  InputTypeIn,
  Popover,
  Text,
} from "@opal/components";
import LineItem from "@/refresh-components/buttons/LineItem";
import {
  SvgAlertTriangle,
  SvgBubbleText,
  SvgDownload,
  SvgEdit,
  SvgEye,
  SvgHistory,
  SvgX,
} from "@opal/icons";
import {
  useDocument,
  useDocumentComments,
  useDocumentVersions,
} from "@/lib/documents/hooks";
import {
  DocumentConflictError,
  createComment,
  deleteComment,
  documentExportUrl,
  replyToComment,
  resolveComment,
  restoreDocumentVersion,
  saveDocument,
  streamAssist,
} from "@/lib/documents/svc";
import { anchorContext } from "@/lib/documents/anchors";
import { useDocumentPanelStore } from "@/lib/documents/store";
import type { AssistMode, DocumentExportFormat } from "@/lib/documents/types";
import DocumentPreview from "@/sections/document-panel/DocumentPreview";
import CommentsPane from "@/sections/document-panel/CommentsPane";
import SelectionMenu from "@/sections/document-panel/SelectionMenu";
import SuggestionTray, {
  type Suggestion,
} from "@/sections/document-panel/SuggestionTray";
import {
  CommentAnchors,
  buildTextIndex,
  commentAnchorsKey,
  resolveAnchors,
  type CommentAnchor,
} from "@/sections/document-panel/commentAnchors";

const AUTOSAVE_DELAY_MS = 1500;
const EXPORT_FORMATS: DocumentExportFormat[] = ["md", "docx", "pdf"];

type SaveStatus = "idle" | "saving" | "saved";

interface DocumentPanelProps {
  documentId: string;
}

export default function DocumentPanel({ documentId }: DocumentPanelProps) {
  const t = useTranslations("documents.panel");
  const closeDocument = useDocumentPanelStore((s) => s.closeDocument);
  const agentRevision = useDocumentPanelStore((s) => s.agentRevision);
  const { document, error, isLoading, mutate } = useDocument(documentId);

  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [previewContent, setPreviewContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [conflict, setConflict] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [useKnowledge, setUseKnowledge] = useState(false);
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [busyCommentId, setBusyCommentId] = useState<string | null>(null);
  const [creatingComment, setCreatingComment] = useState(false);
  const [detachedIds, setDetachedIds] = useState<Set<string>>(new Set());
  const abortRef = useRef<AbortController | null>(null);
  const suggestionTargetRef = useRef<{
    from: number;
    to: number;
    quote: string;
    prefix: string;
    suffix: string;
  } | null>(null);

  const baseVersionRef = useRef(0);
  const dirtyRef = useRef(false);
  const applyingRemoteRef = useRef(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savingRef = useRef(false);
  const savedVersionRef = useRef(0);
  const [savedVersion, setSavedVersion] = useState(0);

  const { comments, mutate: mutateComments } = useDocumentComments(documentId);

  const { versions, mutate: mutateVersions } = useDocumentVersions(
    documentId,
    showHistory
  );

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Markdown,
      Table,
      TableRow,
      TableHeader,
      TableCell,
      CommentAnchors,
    ],
    contentType: "markdown",
    content: "",
    editorProps: {
      attributes: {
        class:
          "prose document-prose max-w-full min-h-full p-4 focus:outline-none",
      },
    },
    onUpdate: () => {
      if (applyingRemoteRef.current) return;
      dirtyRef.current = true;
      setDirty(true);
      setStatus("idle");
      scheduleSave();
    },
  });

  const applyRemote = useCallback(
    (content: string, version: number) => {
      if (!editor) return;
      applyingRemoteRef.current = true;
      editor.commands.setContent(content, { contentType: "markdown" });
      applyingRemoteRef.current = false;
      baseVersionRef.current = version;
      savedVersionRef.current = version;
      setSavedVersion(version);
      dirtyRef.current = false;
      setDirty(false);
      setConflict(false);
      setPreviewContent(content);
    },
    [editor]
  );

  const save = useCallback(async () => {
    if (!editor || savingRef.current || !dirtyRef.current) return;
    savingRef.current = true;
    setStatus("saving");
    const content = editor.getMarkdown();
    try {
      const saved = await saveDocument(documentId, {
        content_md: content,
        base_version: baseVersionRef.current,
      });
      baseVersionRef.current = saved.current_version;
      savedVersionRef.current = saved.current_version;
      setSavedVersion(saved.current_version);
      // Edits made during the request keep the panel dirty and save again.
      const unchanged = editor.getMarkdown() === content;
      dirtyRef.current = !unchanged;
      setDirty(!unchanged);
      setStatus("saved");
      await mutate(saved, { revalidate: false });
      if (!unchanged) scheduleSave();
    } catch (e) {
      setStatus("idle");
      if (e instanceof DocumentConflictError) setConflict(true);
    } finally {
      savingRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor, documentId, mutate]);

  function scheduleSave() {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      void save();
    }, AUTOSAVE_DELAY_MS);
  }

  useEffect(
    () => () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    },
    []
  );

  // Load a new version into the editor unless the user has unsaved edits.
  useEffect(() => {
    if (!document || !editor) return;
    if (document.current_version === baseVersionRef.current) return;
    if (dirtyRef.current) {
      setConflict(true);
      return;
    }
    applyRemote(document.content_md, document.current_version);
  }, [document, editor, applyRemote]);

  // The agent saved a version: fetch it.
  useEffect(() => {
    if (agentRevision > 0) void mutate();
  }, [agentRevision, mutate]);

  async function loadLatest() {
    const latest = await mutate();
    if (latest) applyRemote(latest.content_md, latest.current_version);
  }

  async function keepMine() {
    const latest = await mutate();
    if (!latest) return;
    baseVersionRef.current = latest.current_version;
    setConflict(false);
    await save();
  }

  async function restore(version: number) {
    const restored = await restoreDocumentVersion(documentId, version);
    await mutate(restored, { revalidate: false });
    applyRemote(restored.content_md, restored.current_version);
    await mutateVersions();
  }

  function changeMode(next: "edit" | "preview") {
    if (next === "preview" && editor) setPreviewContent(editor.getMarkdown());
    setMode(next);
  }

  // Draw the quoted text of each open or resolved thread in the editor.
  useEffect(() => {
    if (!editor) return;
    const anchors: CommentAnchor[] = comments
      .filter((c) => c.parent_id === null)
      .map((c) => ({
        id: c.id,
        quote: c.quote,
        prefix: c.prefix,
        suffix: c.suffix,
        resolved: c.resolved,
      }));
    editor.view.dispatch(editor.state.tr.setMeta(commentAnchorsKey, anchors));
    const found = resolveAnchors(editor.state.doc, anchors);
    setDetachedIds(
      new Set(anchors.filter((a) => !found.get(a.id)).map((a) => a.id))
    );
  }, [comments, editor, document?.current_version, previewContent]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    []
  );

  /** The selected text, its anchor and the text around it. */
  function readSelection() {
    if (!editor) return null;
    const { from, to, empty } = editor.state.selection;
    if (empty) return null;
    const { text, positions } = buildTextIndex(editor.state.doc);
    const startIdx = positions.findIndex((p) => p >= from);
    let endIdx = -1;
    for (let i = positions.length - 1; i >= 0; i -= 1) {
      const pos = positions[i];
      if (pos !== undefined && pos < to) {
        endIdx = i;
        break;
      }
    }
    if (startIdx === -1 || endIdx < startIdx) return null;
    const quote = text.slice(startIdx, endIdx + 1);
    const { prefix, suffix } = anchorContext(text, startIdx, endIdx + 1);
    return {
      from,
      to,
      quote,
      prefix,
      suffix,
      before: text.slice(0, startIdx),
      after: text.slice(endIdx + 1),
    };
  }

  async function askComment() {
    const sel = readSelection();
    if (!sel || creatingComment) return;
    setCreatingComment(true);
    setShowComments(true);
    try {
      await createComment(documentId, {
        selection: sel.quote,
        before: sel.before,
        after: sel.after,
        prefix: sel.prefix,
        suffix: sel.suffix,
        body: "",
        instruction,
        use_knowledge: useKnowledge,
        ask_ai: true,
      });
      await mutateComments();
    } finally {
      setCreatingComment(false);
    }
  }

  async function replyComment(id: string, body: string, askAi: boolean) {
    setBusyCommentId(id);
    try {
      await replyToComment(documentId, id, {
        body,
        ask_ai: askAi,
        use_knowledge: useKnowledge,
      });
      await mutateComments();
    } finally {
      setBusyCommentId(null);
    }
  }

  async function changeResolved(id: string, resolved: boolean) {
    await resolveComment(documentId, id, resolved);
    await mutateComments();
  }

  async function removeComment(id: string) {
    await deleteComment(documentId, id);
    await mutateComments();
  }

  function locateComment(id: string) {
    if (!editor) return;
    const anchor = comments.find((c) => c.id === id);
    if (!anchor) return;
    const found = resolveAnchors(editor.state.doc, [
      {
        id,
        quote: anchor.quote,
        prefix: anchor.prefix,
        suffix: anchor.suffix,
        resolved: anchor.resolved,
      },
    ]).get(id);
    if (!found) return;
    setMode("edit");
    editor
      .chain()
      .focus()
      .setTextSelection({ from: found.from, to: found.to })
      .scrollIntoView()
      .run();
  }

  async function startAssist(assistMode: AssistMode, command?: string) {
    const sel = readSelection();
    if (!sel) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    suggestionTargetRef.current = {
      from: sel.from,
      to: sel.to,
      quote: sel.quote,
      prefix: sel.prefix,
      suffix: sel.suffix,
    };
    setSuggestion({
      mode: assistMode,
      text: "",
      status: "streaming",
      error: null,
    });
    try {
      await streamAssist(
        documentId,
        {
          mode: assistMode,
          selection: sel.quote,
          before: sel.before,
          after: sel.after,
          instruction: command ?? instruction,
          use_knowledge: useKnowledge,
        },
        (delta) =>
          setSuggestion((prev) =>
            prev ? { ...prev, text: prev.text + delta } : prev
          ),
        controller.signal
      );
      setSuggestion((prev) => (prev ? { ...prev, status: "done" } : prev));
    } catch (e) {
      if (controller.signal.aborted) {
        setSuggestion((prev) =>
          prev && prev.text ? { ...prev, status: "done" } : null
        );
        return;
      }
      setSuggestion((prev) =>
        prev
          ? {
              ...prev,
              status: "error",
              error: e instanceof Error ? e.message : null,
            }
          : prev
      );
    }
  }

  function stopAssist() {
    abortRef.current?.abort();
  }

  function rejectSuggestion() {
    abortRef.current?.abort();
    suggestionTargetRef.current = null;
    setSuggestion(null);
  }

  function acceptSuggestion(placement: "replace" | "after") {
    const target = suggestionTargetRef.current;
    if (!editor || !suggestion || !target) return;
    // The text may have moved while the AI wrote: find the selection again.
    const found = resolveAnchors(editor.state.doc, [
      {
        id: "target",
        quote: target.quote,
        prefix: target.prefix,
        suffix: target.suffix,
        resolved: false,
      },
    ]).get("target");
    const range = found ?? { from: target.from, to: target.to };
    const size = editor.state.doc.content.size;
    const from = Math.min(range.from, size);
    const to = Math.min(range.to, size);
    if (placement === "replace") {
      editor
        .chain()
        .focus()
        .insertContentAt({ from, to }, suggestion.text, {
          contentType: "markdown",
        })
        .run();
    } else {
      // Continue after the block that holds the end of the selection.
      const resolved = editor.state.doc.resolve(to);
      const insertAt = resolved.depth >= 1 ? resolved.after(1) : to;
      editor
        .chain()
        .focus()
        .insertContentAt(insertAt, suggestion.text, { contentType: "markdown" })
        .run();
    }
    suggestionTargetRef.current = null;
    setSuggestion(null);
  }

  const statusLabel =
    status === "saving"
      ? t("status.saving.label")
      : dirty
        ? t("status.unsaved.label")
        : savedVersion > 0
          ? t("status.saved.label", { version: savedVersion })
          : "";

  return (
    <div className="flex h-full w-full flex-col bg-background-tint-01">
      <div className="flex flex-row items-center justify-between gap-2 px-3 py-2">
        <div className="flex min-w-0 flex-col">
          <Text font="main-ui-action" color="text-04" maxLines={1}>
            {document?.title ?? t("untitled.label")}
          </Text>
          <Text font="secondary-body" color="text-03">
            {statusLabel}
          </Text>
        </div>
        <div className="flex flex-row items-center gap-1">
          <Button
            prominence="tertiary"
            size="sm"
            icon={mode === "edit" ? SvgEye : SvgEdit}
            tooltip={
              mode === "edit" ? t("mode.preview.label") : t("mode.edit.label")
            }
            onClick={() => changeMode(mode === "edit" ? "preview" : "edit")}
          />
          <Button
            prominence="tertiary"
            size="sm"
            icon={SvgHistory}
            tooltip={t("history.label")}
            onClick={() => setShowHistory((v) => !v)}
          />
          <Button
            prominence="tertiary"
            size="sm"
            icon={SvgBubbleText}
            tooltip={t("comments.label")}
            interaction={showComments ? "hover" : "rest"}
            onClick={() => setShowComments((v) => !v)}
          />
          <Popover>
            <Popover.Trigger asChild>
              <Button
                prominence="tertiary"
                size="sm"
                icon={SvgDownload}
                tooltip={t("export.label")}
              />
            </Popover.Trigger>
            <Popover.Content align="end" width="md">
              <Popover.Menu>
                {EXPORT_FORMATS.map((format) => (
                  <LineItem
                    key={format}
                    icon={SvgDownload}
                    href={documentExportUrl(documentId, format)}
                  >
                    {t(`export.${format}.label`)}
                  </LineItem>
                ))}
              </Popover.Menu>
            </Popover.Content>
          </Popover>
          <Button
            prominence="tertiary"
            size="sm"
            icon={SvgX}
            tooltip={t("close.label")}
            onClick={closeDocument}
          />
        </div>
      </div>

      <div className="flex flex-row items-center gap-2 px-3 pb-2">
        <div className="min-w-0 flex-1">
          <InputTypeIn
            value={instruction}
            placeholder={t("assist.instruction.placeholder")}
            onChange={(e) => setInstruction(e.target.value)}
          />
        </div>
        <div className="flex flex-row items-center gap-1">
          <InputSwitch
            checked={useKnowledge}
            onCheckedChange={setUseKnowledge}
          />
          <Text font="secondary-body" color="text-03">
            {t("assist.knowledge.label")}
          </Text>
        </div>
      </div>

      {showComments && (
        <CommentsPane
          comments={comments}
          detachedIds={detachedIds}
          busyId={busyCommentId}
          useKnowledge={useKnowledge}
          onLocate={locateComment}
          onReply={(id, body, askAi) => void replyComment(id, body, askAi)}
          onResolve={(id, resolved) => void changeResolved(id, resolved)}
          onDelete={(id) => void removeComment(id)}
        />
      )}

      {conflict && (
        <div className="mx-3 mb-2 flex flex-col gap-2 rounded-12 border border-status-warning-02 bg-status-warning-01 p-3">
          <div className="flex flex-row items-center gap-2">
            <SvgAlertTriangle className="h-4 w-4 stroke-status-warning-05" />
            <Text font="main-ui-action" color="text-04">
              {t("conflict.title")}
            </Text>
          </div>
          <Text font="secondary-body" color="text-03">
            {t("conflict.body")}
          </Text>
          <div className="flex flex-row gap-2">
            <Button size="sm" onClick={() => void loadLatest()}>
              {t("conflict.loadLatest.label")}
            </Button>
            <Button
              size="sm"
              prominence="secondary"
              onClick={() => void keepMine()}
            >
              {t("conflict.keepMine.label")}
            </Button>
          </div>
        </div>
      )}

      {showHistory && (
        <div className="mx-3 mb-2 flex max-h-48 flex-col gap-1 overflow-y-auto rounded-12 border border-border-01 p-2">
          {versions.map((v) => (
            <div
              key={v.version}
              className="flex flex-row items-center justify-between gap-2"
            >
              <Text font="secondary-body" color="text-03">
                {t("history.entry.label", {
                  version: v.version,
                  author: t(`history.author.${v.author}`),
                })}
              </Text>
              {v.version !== document?.current_version && (
                <Button
                  size="sm"
                  prominence="tertiary"
                  onClick={() => void restore(v.version)}
                >
                  {t("history.restore.label")}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading && (
          <div className="p-4">
            <Text font="main-ui-muted" color="text-03">
              {t("loading.label")}
            </Text>
          </div>
        )}
        {error && !document && (
          <div className="p-4">
            <Text font="main-ui-muted" color="text-03">
              {t("loadFailed.label")}
            </Text>
          </div>
        )}
        <div className={mode === "edit" ? "h-full" : "hidden"}>
          <EditorContent editor={editor} className="h-full" />
          {editor && mode === "edit" && (
            <SelectionMenu
              editor={editor}
              disabled={creatingComment || suggestion?.status === "streaming"}
              onComment={() => void askComment()}
              onAssist={(assistMode, command) =>
                void startAssist(assistMode, command)
              }
            />
          )}
        </div>
        {mode === "preview" && (
          <div className="p-4">
            <DocumentPreview content={previewContent} />
          </div>
        )}
      </div>

      {suggestion && (
        <SuggestionTray
          suggestion={suggestion}
          onAccept={acceptSuggestion}
          onReject={rejectSuggestion}
          onStop={stopAssist}
        />
      )}
    </div>
  );
}
