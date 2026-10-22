export interface DocumentSummary {
  id: string;
  title: string;
  current_version: number;
  chat_session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentSnapshot extends DocumentSummary {
  content_md: string;
  author: "user" | "agent";
}

export interface DocumentVersion {
  version: number;
  author: "user" | "agent";
  summary: string | null;
  created_at: string;
}

export type DocumentExportFormat = "md" | "docx" | "pdf";

export interface DocumentComment {
  id: string;
  parent_id: string | null;
  author: "user" | "ai";
  body: string;
  quote: string;
  prefix: string;
  suffix: string;
  created_on_version: number;
  resolved: boolean;
  created_at: string;
}

/** The text the user selected, with the text around it. */
export interface SelectionContext {
  selection: string;
  before: string;
  after: string;
}

export type AssistMode = "continue" | "rewrite" | "instruct";

export interface AssistOptions {
  instruction: string;
  useKnowledge: boolean;
}
