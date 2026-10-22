"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  DocumentToolFinal,
  Packet,
  PacketType,
} from "@/app/app/services/streamingModels";
import { Button, Text } from "@opal/components";
import { SvgFileText } from "@opal/icons";
import { useDocumentPanelStore } from "@/lib/documents/store";

interface DocumentCardsProps {
  rawPackets: Packet[];
  /** The packet array is mutated in place, so the count drives recomputation. */
  packetCount?: number;
}

interface DocumentEntry {
  docId: string;
  title: string;
  version: number;
}

function collectDocuments(rawPackets: Packet[]): DocumentEntry[] {
  const byId = new Map<string, DocumentEntry>();
  for (const packet of rawPackets) {
    if (packet.obj.type !== PacketType.DOCUMENT_TOOL_FINAL) continue;
    // SAFETY: the type tag was checked on the previous line.
    const final = packet.obj as DocumentToolFinal;
    if (!final.doc_id || final.error || final.action === "read") continue;
    byId.set(final.doc_id, {
      docId: final.doc_id,
      title: final.title ?? "",
      version: final.version ?? 1,
    });
  }
  return Array.from(byId.values());
}

/**
 * Cards for the documents this message wrote. Lives outside the collapsible
 * timeline so the card stays visible. A document that appears while the
 * message is on screen opens the panel; one already saved does not.
 */
export default function DocumentCards({
  rawPackets,
  packetCount,
}: DocumentCardsProps) {
  const t = useTranslations("chat.messages.timeline");
  const openDocument = useDocumentPanelStore((s) => s.openDocument);
  const noteAgentWrite = useDocumentPanelStore((s) => s.noteAgentWrite);

  const count = packetCount ?? rawPackets.length;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const documents = useMemo(() => collectDocuments(rawPackets), [count]);

  // Documents present on first render came from a reloaded chat.
  const [seen] = useState(
    () => new Map(documents.map((d) => [d.docId, d.version]))
  );

  useEffect(() => {
    for (const doc of documents) {
      if (seen.get(doc.docId) === doc.version) continue;
      seen.set(doc.docId, doc.version);
      openDocument(doc.docId);
      noteAgentWrite(doc.docId);
    }
  }, [documents, seen, openDocument, noteAgentWrite]);

  if (documents.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {documents.map((doc) => (
        <div
          key={doc.docId}
          className="flex flex-row items-center justify-between gap-3 rounded-12 border border-border-01 bg-background-neutral-01 px-3 py-2"
        >
          <div className="flex min-w-0 flex-col">
            <Text font="main-ui-action" color="text-04" maxLines={1}>
              {doc.title || t("document.default.status")}
            </Text>
            <Text font="secondary-body" color="text-03">
              {t("document.version.label", { version: doc.version })}
            </Text>
          </div>
          <Button
            prominence="secondary"
            size="sm"
            icon={SvgFileText}
            onClick={() => openDocument(doc.docId)}
          >
            {t("document.open.label")}
          </Button>
        </div>
      ))}
    </div>
  );
}
