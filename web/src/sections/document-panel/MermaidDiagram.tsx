"use client";

import { useEffect, useId, useState } from "react";
import { useTranslations } from "next-intl";
import { Text } from "@opal/components";

interface MermaidDiagramProps {
  code: string;
}

export default function MermaidDiagram({ code }: MermaidDiagramProps) {
  const t = useTranslations("documents.panel");
  const rawId = useId();
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        // "strict" keeps scripts and click handlers out of generated SVG.
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        const { svg: rendered } = await mermaid.render(
          `mermaid-${rawId.replace(/[^a-zA-Z0-9]/g, "")}`,
          code
        );
        if (!cancelled) setSvg(rendered);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, rawId]);

  if (failed) {
    return (
      <div className="flex flex-col gap-1">
        <Text font="secondary-body" color="text-03">
          {t("diagramError.label")}
        </Text>
        <pre className="overflow-x-auto rounded-08 bg-background-neutral-02 p-2 text-sm">
          {code}
        </pre>
      </div>
    );
  }
  if (!svg) return null;
  return (
    <div
      className="flex justify-center overflow-x-auto py-2"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
