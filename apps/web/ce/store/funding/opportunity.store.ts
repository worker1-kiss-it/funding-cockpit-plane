import { action, makeObservable, observable, runInAction } from "mobx";
import { FundingService } from "@/services/funding.service";
import type { RootStore } from "../root.store";

export interface IFundingOpportunityStore {
  detailsMap: Record<string, any>;
  loader: Record<string, boolean>;
  fetchOpportunity: (workspaceSlug: string, projectId: string, issueId: string) => Promise<void>;
  updateOpportunity: (workspaceSlug: string, projectId: string, oppId: string, data: any) => Promise<void>;
  getByIssueId: (issueId: string) => any | undefined;
}

export class FundingOpportunityStore implements IFundingOpportunityStore {
  // Map issue_id -> funding opportunity data
  detailsMap: Record<string, any> = {};
  loader: Record<string, boolean> = {};
  private service: FundingService;

  constructor(private rootStore: RootStore) {
    makeObservable(this, {
      detailsMap: observable,
      loader: observable,
      fetchOpportunity: action,
      updateOpportunity: action,
    });
    this.service = new FundingService();
  }

  getByIssueId = (issueId: string): any | undefined => {
    return this.detailsMap[issueId];
  };

  fetchOpportunity = async (workspaceSlug: string, projectId: string, issueId: string) => {
    // The API returns opportunities by their own UUID, but we look up by issue ID
    // First check if we already have it cached
    if (this.detailsMap[issueId]) return;

    this.loader[issueId] = true;
    try {
      // Use pipeline endpoint to find opportunity by issue ID
      const pipeline = await this.service.getPipeline(workspaceSlug, projectId);
      const opportunities = pipeline?.opportunities || [];
      for (const opp of opportunities) {
        runInAction(() => {
          this.detailsMap[opp.issue] = opp;
        });
      }
    } catch {
      // silently fail
    } finally {
      runInAction(() => { this.loader[issueId] = false; });
    }
  };

  updateOpportunity = async (workspaceSlug: string, projectId: string, oppId: string, data: any) => {
    try {
      const updated = await this.service.updateOpportunity(workspaceSlug, projectId, oppId, data);
      runInAction(() => {
        if (updated?.issue) {
          this.detailsMap[updated.issue] = updated;
        }
      });
    } catch {
      // silently fail
    }
  };
}
