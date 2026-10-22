"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import MermaidDiagram from "@/sections/document-panel/MermaidDiagram";

const components: Components = {
  code({ className, children, ...rest }) {
    const language = /language-(\w+)/.exec(className ?? "")?.[1];
    if (language === "mermaid") {
      return <MermaidDiagram code={String(children).replace(/\n$/, "")} />;
    }
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  },
};

interface DocumentPreviewProps {
  content: string;
}

export default function DocumentPreview({ content }: DocumentPreviewProps) {
  return (
    <div className="prose document-prose max-w-full">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
