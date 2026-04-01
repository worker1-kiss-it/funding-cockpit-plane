import { action, makeObservable, observable, runInAction } from "mobx";
import { FundingService } from "@/services/funding.service";
import type { RootStore } from "../root.store";

export interface IChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
}

export interface IFundingChatStore {
  messages: IChatMessage[];
  isOpen: boolean;
  isLoading: boolean;
  historyLoaded: boolean;
  toggleDrawer: () => void;
  sendMessage: (workspaceSlug: string, projectId: string, message: string) => Promise<void>;
  fetchHistory: (workspaceSlug: string, projectId: string) => Promise<void>;
}

export class FundingChatStore implements IFundingChatStore {
  messages: IChatMessage[] = [];
  isOpen = false;
  isLoading = false;
  historyLoaded = false;
  private service: FundingService;

  constructor(private rootStore: RootStore) {
    makeObservable(this, {
      messages: observable,
      isOpen: observable,
      isLoading: observable,
      historyLoaded: observable,
      toggleDrawer: action,
      sendMessage: action,
      fetchHistory: action,
    });
    this.service = new FundingService();
  }

  toggleDrawer = () => {
    this.isOpen = !this.isOpen;
  };

  fetchHistory = async (workspaceSlug: string, projectId: string) => {
    if (this.historyLoaded) return;
    try {
      const data = await this.service.getChatHistory(workspaceSlug, projectId);
      runInAction(() => {
        this.messages = (data?.messages || []).map((m: any) => ({
          role: m.role,
          content: m.content,
        }));
        this.historyLoaded = true;
      });
    } catch {
      // silently fail
    }
  };

  sendMessage = async (workspaceSlug: string, projectId: string, message: string) => {
    // Optimistically add user message
    this.messages.push({ role: "user", content: message, timestamp: new Date().toISOString() });
    this.isLoading = true;
    try {
      const data = await this.service.sendChatMessage(workspaceSlug, projectId, message);
      runInAction(() => {
        this.messages.push({
          role: "assistant",
          content: data?.response || "No response received.",
          timestamp: new Date().toISOString(),
        });
      });
    } catch {
      runInAction(() => {
        this.messages.push({
          role: "system",
          content: "Failed to get a response. Please try again.",
        });
      });
    } finally {
      runInAction(() => { this.isLoading = false; });
    }
  };
}
