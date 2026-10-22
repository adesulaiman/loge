"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Button, InputTypeIn, Text } from "@opal/components";
import { SvgCheck, SvgTrash } from "@opal/icons";
import type { DocumentComment } from "@/lib/documents/types";

interface CommentsPaneProps {
  comments: DocumentComment[];
  /** Ids of comments whose quoted text is no longer in the document. */
  detachedIds: Set<string>;
  busyId: string | null;
  useKnowledge: boolean;
  onLocate: (id: string) => void;
  onReply: (id: string, body: string, askAi: boolean) => void;
  onResolve: (id: string, resolved: boolean) => void;
  onDelete: (id: string) => void;
}

function Thread({
  root,
  replies,
  detached,
  busy,
  onLocate,
  onReply,
  onResolve,
  onDelete,
}: {
  root: DocumentComment;
  replies: DocumentComment[];
  detached: boolean;
  busy: boolean;
  onLocate: () => void;
  onReply: (body: string, askAi: boolean) => void;
  onResolve: (resolved: boolean) => void;
  onDelete: () => void;
}) {
  const t = useTranslations("documents.panel.comments");
  const [draft, setDraft] = useState("");

  function send(askAi: boolean) {
    if (!askAi && !draft.trim()) return;
    onReply(draft, askAi);
    setDraft("");
  }

  return (
    <div className="flex flex-col gap-2 rounded-12 border border-border-01 p-2">
      <button type="button" className="text-start" onClick={onLocate}>
        <Text font="secondary-body" color="text-03" maxLines={2}>
          {`“${root.quote}”`}
        </Text>
      </button>
      {detached && (
        <Text font="secondary-body" color="text-03">
          {t("detached.label")}
        </Text>
      )}
      {[root, ...replies].map((comment) => (
        <div key={comment.id} className="flex flex-col">
          <Text font="secondary-action" color="text-04">
            {comment.author === "ai" ? t("author.ai") : t("author.user")}
          </Text>
          <Text font="main-ui-body" color="text-04">
            {comment.body}
          </Text>
        </div>
      ))}
      {!root.resolved && (
        <div className="flex flex-col gap-1">
          <InputTypeIn
            value={draft}
            placeholder={t("reply.placeholder")}
            onChange={(e) => setDraft(e.target.value)}
            variant={busy ? "disabled" : "primary"}
          />
          <div className="flex flex-row flex-wrap gap-1">
            <Button
              size="sm"
              prominence="secondary"
              disabled={busy || !draft.trim()}
              onClick={() => send(false)}
            >
              {t("reply.label")}
            </Button>
            <Button
              size="sm"
              prominence="secondary"
              disabled={busy}
              onClick={() => send(true)}
            >
              {busy ? t("asking.label") : t("askAi.label")}
            </Button>
          </div>
        </div>
      )}
      <div className="flex flex-row gap-1">
        <Button
          size="sm"
          prominence="tertiary"
          icon={SvgCheck}
          onClick={() => onResolve(!root.resolved)}
        >
          {root.resolved ? t("reopen.label") : t("resolve.label")}
        </Button>
        <Button
          size="sm"
          prominence="tertiary"
          icon={SvgTrash}
          onClick={onDelete}
        >
          {t("delete.label")}
        </Button>
      </div>
    </div>
  );
}

export default function CommentsPane({
  comments,
  detachedIds,
  busyId,
  onLocate,
  onReply,
  onResolve,
  onDelete,
}: CommentsPaneProps) {
  const t = useTranslations("documents.panel.comments");
  const threads = useMemo(() => {
    const roots = comments.filter((c) => c.parent_id === null);
    return roots.map((root) => ({
      root,
      replies: comments.filter((c) => c.parent_id === root.id),
    }));
  }, [comments]);

  return (
    <div className="mx-3 mb-2 flex max-h-72 flex-col gap-2 overflow-y-auto">
      {threads.length === 0 && (
        <Text font="secondary-body" color="text-03">
          {t("empty.label")}
        </Text>
      )}
      {threads.map(({ root, replies }) => (
        <Thread
          key={root.id}
          root={root}
          replies={replies}
          detached={detachedIds.has(root.id)}
          busy={busyId === root.id}
          onLocate={() => onLocate(root.id)}
          onReply={(body, askAi) => onReply(root.id, body, askAi)}
          onResolve={(resolved) => onResolve(root.id, resolved)}
          onDelete={() => onDelete(root.id)}
        />
      ))}
    </div>
  );
}
