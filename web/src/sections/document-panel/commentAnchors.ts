import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { locateQuote } from "@/lib/documents/anchors";

export interface CommentAnchor {
  id: string;
  quote: string;
  prefix: string;
  suffix: string;
  resolved: boolean;
}

interface TextIndex {
  text: string;
  /** Document position of each character in text. */
  positions: number[];
}

export const commentAnchorsKey = new PluginKey<CommentAnchor[]>(
  "commentAnchors"
);

/** Flatten the document to plain text, keeping the position of each character. */
export function buildTextIndex(doc: ProseMirrorNode): TextIndex {
  let text = "";
  const positions: number[] = [];
  doc.descendants((node, pos) => {
    if (node.isText && node.text) {
      for (let i = 0; i < node.text.length; i += 1) {
        positions.push(pos + i);
      }
      text += node.text;
    } else if (node.isBlock && text && !text.endsWith("\n")) {
      positions.push(pos);
      text += "\n";
    }
    return true;
  });
  return { text, positions };
}

/** Where each anchor sits in the document, or null when its text is gone. */
export function resolveAnchors(
  doc: ProseMirrorNode,
  anchors: CommentAnchor[]
): Map<string, { from: number; to: number } | null> {
  const index = buildTextIndex(doc);
  const result = new Map<string, { from: number; to: number } | null>();
  for (const anchor of anchors) {
    const match = locateQuote(
      index.text,
      anchor.quote,
      anchor.prefix,
      anchor.suffix
    );
    const first = match ? index.positions[match.start] : undefined;
    const last = match ? index.positions[match.end - 1] : undefined;
    result.set(
      anchor.id,
      first !== undefined && last !== undefined
        ? { from: first, to: last + 1 }
        : null
    );
  }
  return result;
}

function decorate(doc: ProseMirrorNode, anchors: CommentAnchor[]) {
  const found = resolveAnchors(doc, anchors);
  const decorations: Decoration[] = [];
  for (const anchor of anchors) {
    const range = found.get(anchor.id);
    if (!range) continue;
    decorations.push(
      Decoration.inline(range.from, range.to, {
        class: anchor.resolved
          ? "doc-comment doc-comment--resolved"
          : "doc-comment",
        "data-comment-id": anchor.id,
      })
    );
  }
  return DecorationSet.create(doc, decorations);
}

/** Highlights the quoted text of comments. The text of the document is never changed. */
export const CommentAnchors = Extension.create({
  name: "commentAnchors",
  addProseMirrorPlugins() {
    return [
      new Plugin<CommentAnchor[]>({
        key: commentAnchorsKey,
        state: {
          init: () => [],
          apply(transaction, anchors) {
            const next: CommentAnchor[] | undefined =
              transaction.getMeta(commentAnchorsKey);
            return next ?? anchors;
          },
        },
        props: {
          decorations(state) {
            const anchors = commentAnchorsKey.getState(state) ?? [];
            return anchors.length === 0 ? null : decorate(state.doc, anchors);
          },
        },
      }),
    ];
  },
});
