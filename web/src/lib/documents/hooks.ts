"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { SWR_KEYS } from "@/lib/swr-keys";
import type {
  DocumentComment,
  DocumentSnapshot,
  DocumentVersion,
} from "@/lib/documents/types";

export function useDocument(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<DocumentSnapshot>(
    id ? SWR_KEYS.document(id) : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  return { document: data ?? null, error, isLoading, mutate };
}

export function useDocumentVersions(id: string | null, enabled: boolean) {
  const { data, mutate } = useSWR<DocumentVersion[]>(
    id && enabled ? SWR_KEYS.documentVersions(id) : null,
    errorHandlingFetcher
  );
  return { versions: data ?? [], mutate };
}

export function useDocumentComments(id: string | null) {
  const { data, mutate } = useSWR<DocumentComment[]>(
    id ? SWR_KEYS.documentComments(id) : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  return { comments: data ?? [], mutate };
}
