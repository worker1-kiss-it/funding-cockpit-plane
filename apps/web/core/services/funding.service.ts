import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

export class FundingService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private fundingUrl(workspaceSlug: string, projectId: string, path: string): string {
    return `/api/funding/workspaces/${workspaceSlug}/projects/${projectId}/funding/${path}`;
  }

  // Dashboard
  async getDashboard(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "dashboard/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async getDeadlines(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "deadlines/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async getPipeline(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "pipeline/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Opportunity detail
  async getOpportunity(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async updateOpportunity(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Knowledge Base
  async getKbTree(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "kb/tree/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async getKbFile(workspaceSlug: string, projectId: string, path: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `kb/file/?path=${encodeURIComponent(path)}`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  getKbFileRawUrl(workspaceSlug: string, projectId: string, path: string): string {
    return `${API_BASE_URL}${this.fundingUrl(workspaceSlug, projectId, `kb/file/raw/?path=${encodeURIComponent(path)}`)}`;
  }

  async searchKb(workspaceSlug: string, projectId: string, query: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `kb/search/?q=${encodeURIComponent(query)}`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async getKbProjects(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "kb/projects/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Proposals
  async getProposals(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async createProposal(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async updateProposal(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async deleteProposal(workspaceSlug: string, projectId: string, oppId: string, pk: string): Promise<any> {
    return this.delete(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/${pk}/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Partners
  async getPartners(workspaceSlug: string): Promise<any> {
    return this.get(`/api/funding/workspaces/${workspaceSlug}/funding/partners/`)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async createPartner(workspaceSlug: string, data: any): Promise<any> {
    return this.post(`/api/funding/workspaces/${workspaceSlug}/funding/partners/`, data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Consortium
  async getConsortium(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/consortium/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async addConsortiumMember(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/consortium/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Meetings
  async getMeetings(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async createMeeting(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async updateMeeting(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // Milestones
  async getMilestones(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/`))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async createMilestone(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async updateMilestone(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  // AI Chat
  async sendChatMessage(workspaceSlug: string, projectId: string, message: string): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, "chat/send/"), { message })
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }

  async getChatHistory(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "chat/history/"))
      .then((res) => res?.data)
      .catch((err) => { throw err?.response?.data; });
  }
}
