import { action, makeObservable, observable, runInAction } from "mobx";
import { FundingService } from "@/services/funding.service";
import type { RootStore } from "../root.store";

export interface IKbStore {
  tree: any | null;
  currentFilePath: string | null;
  currentFileContent: any | null;
  searchResults: any[];
  searchQuery: string;
  loader: boolean;
  fetchTree: (workspaceSlug: string, projectId: string) => Promise<void>;
  fetchFile: (workspaceSlug: string, projectId: string, path: string) => Promise<void>;
  searchFiles: (workspaceSlug: string, projectId: string, query: string) => Promise<void>;
  clearFile: () => void;
}

export class KbStore implements IKbStore {
  tree: any | null = null;
  currentFilePath: string | null = null;
  currentFileContent: any | null = null;
  searchResults: any[] = [];
  searchQuery = "";
  loader = false;
  private service: FundingService;

  constructor(private rootStore: RootStore) {
    makeObservable(this, {
      tree: observable,
      currentFilePath: observable,
      currentFileContent: observable,
      searchResults: observable,
      searchQuery: observable,
      loader: observable,
      fetchTree: action,
      fetchFile: action,
      searchFiles: action,
      clearFile: action,
    });
    this.service = new FundingService();
  }

  fetchTree = async (workspaceSlug: string, projectId: string) => {
    try {
      const data = await this.service.getKbTree(workspaceSlug, projectId);
      runInAction(() => { this.tree = data; });
    } catch {
      // silently fail
    }
  };

  fetchFile = async (workspaceSlug: string, projectId: string, path: string) => {
    this.loader = true;
    this.currentFilePath = path;
    try {
      const data = await this.service.getKbFile(workspaceSlug, projectId, path);
      runInAction(() => { this.currentFileContent = data; });
    } catch {
      runInAction(() => { this.currentFileContent = { error: "Failed to load file" }; });
    } finally {
      runInAction(() => { this.loader = false; });
    }
  };

  searchFiles = async (workspaceSlug: string, projectId: string, query: string) => {
    this.searchQuery = query;
    if (query.length < 2) {
      this.searchResults = [];
      return;
    }
    try {
      const data = await this.service.searchKb(workspaceSlug, projectId, query);
      runInAction(() => { this.searchResults = data?.results || []; });
    } catch {
      // silently fail
    }
  };

  clearFile = () => {
    this.currentFilePath = null;
    this.currentFileContent = null;
  };
}
