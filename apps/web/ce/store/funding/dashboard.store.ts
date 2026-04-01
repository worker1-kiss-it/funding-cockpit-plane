import { action, makeObservable, observable, runInAction } from "mobx";
import { FundingService } from "@/services/funding.service";
import type { RootStore } from "../root.store";

export interface IFundingDashboardStore {
  stats: Record<string, any> | null;
  deadlines: any[];
  loader: boolean;
  fetchDashboard: (workspaceSlug: string, projectId: string) => Promise<void>;
  fetchDeadlines: (workspaceSlug: string, projectId: string) => Promise<void>;
}

export class FundingDashboardStore implements IFundingDashboardStore {
  stats: Record<string, any> | null = null;
  deadlines: any[] = [];
  loader = false;
  private service: FundingService;

  constructor(private rootStore: RootStore) {
    makeObservable(this, {
      stats: observable,
      deadlines: observable,
      loader: observable,
      fetchDashboard: action,
      fetchDeadlines: action,
    });
    this.service = new FundingService();
  }

  fetchDashboard = async (workspaceSlug: string, projectId: string) => {
    this.loader = true;
    try {
      const data = await this.service.getDashboard(workspaceSlug, projectId);
      runInAction(() => {
        this.stats = data;
      });
    } finally {
      runInAction(() => { this.loader = false; });
    }
  };

  fetchDeadlines = async (workspaceSlug: string, projectId: string) => {
    try {
      const data = await this.service.getDeadlines(workspaceSlug, projectId);
      runInAction(() => {
        this.deadlines = data?.deadlines || [];
      });
    } catch {
      // silently fail
    }
  };
}
