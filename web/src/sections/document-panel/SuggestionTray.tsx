"use client";

import { useTranslations } from "next-intl";
import { Button, Text } from "@opal/components";
import { SvgCheck, SvgX } from "@opal/icons";
import type { AssistMode } from "@/lib/documents/types";
import DocumentPreview from "@/sections/document-panel/DocumentPreview";

export type SuggestionStatus = "streaming" | "done" | "error";

export interface Suggestion {
  mode: AssistMode;
  text: string;
  status: SuggestionStatus;
  error: string | null;
}

interface SuggestionTrayProps {
  suggestion: Suggestion;
  onAccept: (placement: "replace" | "after") => void;
  onReject: () => void;
  onStop: () => void;
}

/** The AI's streamed text. Nothing enters the document until the user accepts. */
export default function SuggestionTray({
  suggestion,
  onAccept,
  onReject,
  onStop,
}: SuggestionTrayProps) {
  const t = useTranslations("documents.panel.suggestion");
  const streaming = suggestion.status === "streaming";
  return (
    <div className="mx-3 mb-3 flex max-h-72 flex-col gap-2 rounded-12 border border-border-02 bg-background-neutral-01 p-3">
      <Text font="main-ui-action" color="text-04">
        {t(`${suggestion.mode}.title`)}
      </Text>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {suggestion.status === "error" ? (
          <Text font="secondary-body" color="text-03">
            {suggestion.error ?? t("error.label")}
          </Text>
        ) : (
          <DocumentPreview content={suggestion.text} />
        )}
      </div>
      <div className="flex flex-row gap-2">
        {streaming ? (
          <Button size="sm" prominence="secondary" onClick={onStop}>
            {t("stop.label")}
          </Button>
        ) : (
          <>
            {suggestion.status === "done" && suggestion.text.trim() && (
              <>
                {suggestion.mode !== "continue" && (
                  <Button
                    size="sm"
                    icon={SvgCheck}
                    onClick={() => onAccept("replace")}
                  >
                    {suggestion.mode === "rewrite"
                      ? t("accept.label")
                      : t("replace.label")}
                  </Button>
                )}
                {suggestion.mode !== "rewrite" && (
                  <Button
                    size="sm"
                    prominence={
                      suggestion.mode === "instruct" ? "secondary" : "primary"
                    }
                    icon={SvgCheck}
                    onClick={() => onAccept("after")}
                  >
                    {suggestion.mode === "continue"
                      ? t("accept.label")
                      : t("insertBelow.label")}
                  </Button>
                )}
              </>
            )}
            <Button
              size="sm"
              prominence="secondary"
              icon={SvgX}
              onClick={onReject}
            >
              {t("reject.label")}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
