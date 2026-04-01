import type { RootStore } from "../root.store";
import { FundingDashboardStore, type IFundingDashboardStore } from "./dashboard.store";
import { KbStore, type IKbStore } from "./kb.store";
import { FundingChatStore, type IFundingChatStore } from "./chat.store";
import { FundingOpportunityStore, type IFundingOpportunityStore } from "./opportunity.store";

export interface IFundingStore {
  dashboard: IFundingDashboardStore;
  kb: IKbStore;
  chat: IFundingChatStore;
  opportunity: IFundingOpportunityStore;
}

export class FundingStore implements IFundingStore {
  dashboard: IFundingDashboardStore;
  kb: IKbStore;
  chat: IFundingChatStore;
  opportunity: IFundingOpportunityStore;

  constructor(rootStore: RootStore) {
    this.dashboard = new FundingDashboardStore(rootStore);
    this.kb = new KbStore(rootStore);
    this.chat = new FundingChatStore(rootStore);
    this.opportunity = new FundingOpportunityStore(rootStore);
  }
}
