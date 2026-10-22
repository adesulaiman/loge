import { useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  DocumentToolFinal,
  DocumentToolPacket,
  PacketType,
} from "@/app/app/services/streamingModels";
import {
  MessageRenderer,
  RenderType,
} from "@/app/app/message/messageComponents/interfaces";
import { Button, Text } from "@opal/components";
import { SvgFileText } from "@opal/icons";
import { useDocumentPanelStore } from "@/lib/documents/store";

export const DocumentToolRenderer: MessageRenderer<DocumentToolPacket, {}> = ({
  packets,
  onComplete,
  renderType,
  children,
}) => {
  const t = useTranslations("chat.messages.timeline");
  const openDocument = useDocumentPanelStore((s) => s.openDocument);

  const final = useMemo(
    () =>
      packets.find((p) => p.obj.type === PacketType.DOCUMENT_TOOL_FINAL)
        ?.obj as DocumentToolFinal | undefined,
    [packets]
  );
  const ended = packets.some(
    (p) =>
      p.obj.type === PacketType.SECTION_END || p.obj.type === PacketType.ERROR
  );
  const docId = final?.doc_id ?? null;
  const isWrite = !!final && final.action !== "read";

  useEffect(() => {
    if (ended) onComplete();
  }, [ended, onComplete]);

  const status = !ended
    ? t("document.writing.status")
    : final?.error || !docId
      ? t("document.failed.status")
      : isWrite
        ? t("document.saved.status")
        : t("document.default.status");

  const content = (
    <div className="flex flex-row items-center justify-between gap-3 rounded-12 border border-border-01 bg-background-neutral-01 px-3 py-2">
      <div className="flex flex-col min-w-0">
        <Text font="main-ui-action" color="text-04" maxLines={1}>
          {final?.title ?? t("document.default.status")}
        </Text>
        {final?.version != null && (
          <Text font="secondary-body" color="text-03">
            {t("document.version.label", { version: final.version })}
          </Text>
        )}
      </div>
      {docId && (
        <Button
          prominence="secondary"
          size="sm"
          icon={SvgFileText}
          onClick={() => openDocument(docId)}
        >
          {t("document.open.label")}
        </Button>
      )}
    </div>
  );

  return children([
    {
      icon: SvgFileText,
      status,
      content,
      supportsCollapsible: renderType !== RenderType.HIGHLIGHT,
      alwaysCollapsible: false,
    },
  ]);
};
