import { create } from "zustand";

interface DocumentPanelState {
  openDocumentId: string | null;
  /** Bumped when the agent saves a new version, so the open panel reloads. */
  agentRevision: number;
  openDocument: (id: string) => void;
  closeDocument: () => void;
  noteAgentWrite: (id: string) => void;
}

export const useDocumentPanelStore = create<DocumentPanelState>((set, get) => ({
  openDocumentId: null,
  agentRevision: 0,
  openDocument: (id) => set({ openDocumentId: id }),
  closeDocument: () => set({ openDocumentId: null }),
  noteAgentWrite: (id) => {
    if (get().openDocumentId === id) {
      set((state) => ({ agentRevision: state.agentRevision + 1 }));
    }
  },
}));
