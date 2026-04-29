import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { FundingService } from "@/services/funding.service";
import type { RootStore } from "../root.store";

export interface IChatMessage {
  id?: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  created_at?: string;
  tokens_in?: number | null;
  tokens_out?: number | null;
  cost_usd?: number | null;
  /** True while the assistant turn is still streaming. */
  streaming?: boolean;
}

export interface IChatSession {
  id: string;
  claude_session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface IFundingChatStore {
  isOpen: boolean;
  isLoading: boolean;
  isStreaming: boolean;
  sessions: IChatSession[];
  activeSessionId: string | null;
  messages: IChatMessage[];
  toggleDrawer: () => void;
  loadSessions: (workspaceSlug: string, projectId: string) => Promise<void>;
  startNewSession: (workspaceSlug: string, projectId: string) => Promise<void>;
  selectSession: (workspaceSlug: string, projectId: string, sessionId: string) => Promise<void>;
  sendMessage: (workspaceSlug: string, projectId: string, message: string) => Promise<void>;
}

export class FundingChatStore implements IFundingChatStore {
  isOpen = false;
  isLoading = false;
  isStreaming = false;
  sessions: IChatSession[] = [];
  activeSessionId: string | null = null;
  messages: IChatMessage[] = [];
  private service: FundingService;
  private abortController: AbortController | null = null;

  constructor(private rootStore: RootStore) {
    makeObservable(this, {
      isOpen: observable,
      isLoading: observable,
      isStreaming: observable,
      sessions: observable,
      activeSessionId: observable,
      messages: observable,
      activeSession: computed,
      toggleDrawer: action,
      loadSessions: action,
      startNewSession: action,
      selectSession: action,
      sendMessage: action,
    });
    this.service = new FundingService();
  }

  get activeSession() {
    return this.sessions.find((s) => s.id === this.activeSessionId) || null;
  }

  toggleDrawer = () => {
    this.isOpen = !this.isOpen;
  };

  loadSessions = async (workspaceSlug: string, projectId: string) => {
    try {
      const data = await this.service.listChatSessions(workspaceSlug, projectId);
      runInAction(() => {
        this.sessions = data?.sessions || [];
      });
    } catch {
      // ignore
    }
  };

  startNewSession = async (workspaceSlug: string, projectId: string) => {
    try {
      const session = await this.service.createChatSession(workspaceSlug, projectId);
      runInAction(() => {
        this.sessions = [session, ...this.sessions];
        this.activeSessionId = session.id;
        this.messages = [];
      });
    } catch {
      // ignore
    }
  };

  selectSession = async (workspaceSlug: string, projectId: string, sessionId: string) => {
    runInAction(() => {
      this.activeSessionId = sessionId;
      this.messages = [];
      this.isLoading = true;
    });
    try {
      const data = await this.service.listChatMessages(workspaceSlug, projectId, sessionId);
      runInAction(() => {
        this.messages = data?.messages || [];
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  sendMessage = async (workspaceSlug: string, projectId: string, message: string) => {
    // If no active session, start one first.
    if (!this.activeSessionId) {
      await this.startNewSession(workspaceSlug, projectId);
    }
    const sessionId = this.activeSessionId;
    if (!sessionId) return;

    // Optimistically append the user message and a placeholder assistant message.
    runInAction(() => {
      this.messages.push({ id: crypto.randomUUID(), role: "user", content: message });
      this.messages.push({ id: crypto.randomUUID(), role: "assistant", content: "", streaming: true });
      this.isStreaming = true;
    });
    const assistantIndex = this.messages.length - 1;

    this.abortController = new AbortController();
    try {
      await this.service.streamChatMessage(
        workspaceSlug,
        projectId,
        sessionId,
        message,
        (event) => {
          runInAction(() => {
            const msg = this.messages[assistantIndex];
            if (!msg) return;
            if (event.type === "delta" && typeof event.text === "string") {
              msg.content += event.text;
            } else if (event.type === "done") {
              msg.streaming = false;
              msg.id = event.message_id;
              msg.tokens_in = event.tokens_in ?? null;
              msg.tokens_out = event.tokens_out ?? null;
              msg.cost_usd = event.cost_usd ?? null;
            } else if (event.type === "error") {
              msg.role = "system";
              msg.content = event.message || "error";
              msg.streaming = false;
            }
          });
        },
        this.abortController.signal
      );
    } catch (e: any) {
      runInAction(() => {
        const msg = this.messages[assistantIndex];
        if (msg) {
          msg.role = "system";
          msg.content = e?.message || "Failed to reach the assistant";
          msg.streaming = false;
        }
      });
    } finally {
      runInAction(() => {
        this.isStreaming = false;
        this.abortController = null;
      });
      // Refresh session list so titles/timestamps update
      void this.loadSessions(workspaceSlug, projectId);
    }
  };
}
