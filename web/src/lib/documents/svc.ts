import type {
  AssistMode,
  DocumentComment,
  DocumentSnapshot,
} from "@/lib/documents/types";

export class DocumentConflictError extends Error {
  constructor() {
    super("Document changed");
    this.name = "DocumentConflictError";
  }
}

export async function saveDocument(
  id: string,
  body: { content_md: string; base_version: number; title?: string }
): Promise<DocumentSnapshot> {
  const response = await fetch(`/api/documents/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (response.status === 409) {
    throw new DocumentConflictError();
  }
  if (!response.ok) {
    throw new Error(`Save document failed (Status: ${response.status})`);
  }
  return response.json();
}

export async function restoreDocumentVersion(
  id: string,
  version: number
): Promise<DocumentSnapshot> {
  const response = await fetch(`/api/documents/${id}/restore/${version}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Restore version failed (Status: ${response.status})`);
  }
  return response.json();
}

export function documentExportUrl(id: string, format: string): string {
  return `/api/documents/${id}/export?format=${format}`;
}

async function readJson<T>(response: Response, action: string): Promise<T> {
  if (!response.ok) {
    throw new Error(`${action} failed (Status: ${response.status})`);
  }
  return response.json();
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function createComment(
  documentId: string,
  body: {
    selection: string;
    before: string;
    after: string;
    prefix: string;
    suffix: string;
    body: string;
    instruction: string;
    use_knowledge: boolean;
    ask_ai: boolean;
  }
): Promise<DocumentComment[]> {
  const response = await fetch(`/api/documents/${documentId}/comments`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
  return readJson(response, "Create comment");
}

export async function replyToComment(
  documentId: string,
  commentId: string,
  body: { body: string; ask_ai: boolean; use_knowledge: boolean }
): Promise<DocumentComment[]> {
  const response = await fetch(
    `/api/documents/${documentId}/comments/${commentId}/replies`,
    { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) }
  );
  return readJson(response, "Reply to comment");
}

export async function resolveComment(
  documentId: string,
  commentId: string,
  resolved: boolean
): Promise<DocumentComment> {
  const response = await fetch(
    `/api/documents/${documentId}/comments/${commentId}`,
    {
      method: "PATCH",
      headers: JSON_HEADERS,
      body: JSON.stringify({ resolved }),
    }
  );
  return readJson(response, "Resolve comment");
}

export async function deleteComment(
  documentId: string,
  commentId: string
): Promise<void> {
  const response = await fetch(
    `/api/documents/${documentId}/comments/${commentId}`,
    { method: "DELETE" }
  );
  if (!response.ok) {
    throw new Error(`Delete comment failed (Status: ${response.status})`);
  }
}

/**
 * Stream a continuation or rewrite. Calls onDelta for each piece of text and
 * throws on an error line. Abort with the signal.
 */
export async function streamAssist(
  documentId: string,
  body: {
    mode: AssistMode;
    selection: string;
    before: string;
    after: string;
    instruction: string;
    use_knowledge: boolean;
  },
  onDelta: (text: string) => void,
  signal: AbortSignal
): Promise<void> {
  const response = await fetch(`/api/documents/${documentId}/ai/stream`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`AI request failed (Status: ${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const handleLine = (line: string) => {
    if (!line.trim()) return;
    const parsed: { delta?: string; error?: string } = JSON.parse(line);
    if (parsed.error) throw new Error(parsed.error);
    if (parsed.delta) onDelta(parsed.delta);
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    lines.forEach(handleLine);
  }
  handleLine(buffer);
}
