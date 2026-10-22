"use client";

import { useState } from "react";
import type { Editor } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";
import { useTranslations } from "next-intl";
import { Button, InputTypeIn } from "@opal/components";
import { SvgBubbleText, SvgRefreshCw, SvgSparkle } from "@opal/icons";
import type { AssistMode } from "@/lib/documents/types";

interface SelectionMenuProps {
  editor: Editor;
  disabled: boolean;
  onComment: () => void;
  onAssist: (mode: AssistMode, instruction?: string) => void;
}

/** Floating actions shown over selected text. */
export default function SelectionMenu({
  editor,
  disabled,
  onComment,
  onAssist,
}: SelectionMenuProps) {
  const t = useTranslations("documents.panel.selection");
  const [command, setCommand] = useState("");

  function runCommand() {
    if (!command.trim() || disabled) return;
    onAssist("instruct", command.trim());
    setCommand("");
  }

  return (
    <BubbleMenu
      editor={editor}
      options={{ placement: "top" }}
      className="flex flex-col gap-1 rounded-12 border border-border-01 bg-background-neutral-00 p-1 shadow-02"
    >
      <div className="flex flex-row gap-1">
        <Button
          prominence="tertiary"
          size="sm"
          icon={SvgBubbleText}
          disabled={disabled}
          onClick={onComment}
        >
          {t("comment.label")}
        </Button>
        <Button
          prominence="tertiary"
          size="sm"
          icon={SvgSparkle}
          disabled={disabled}
          onClick={() => onAssist("continue")}
        >
          {t("continue.label")}
        </Button>
        <Button
          prominence="tertiary"
          size="sm"
          icon={SvgRefreshCw}
          disabled={disabled}
          onClick={() => onAssist("rewrite")}
        >
          {t("rewrite.label")}
        </Button>
      </div>
      <form
        className="flex flex-row items-center gap-1"
        onSubmit={(e) => {
          e.preventDefault();
          runCommand();
        }}
      >
        <div className="w-64">
          <InputTypeIn
            value={command}
            placeholder={t("instruct.placeholder")}
            onChange={(e) => setCommand(e.target.value)}
          />
        </div>
        <Button
          size="sm"
          icon={SvgSparkle}
          type="submit"
          disabled={disabled || !command.trim()}
        >
          {t("instruct.label")}
        </Button>
      </form>
    </BubbleMenu>
  );
}
