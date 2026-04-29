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
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getDeadlines(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "deadlines/"))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getPipeline(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "pipeline/"))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Opportunity detail
  async getOpportunity(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateOpportunity(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Knowledge Base
  async getKbTree(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "kb/tree/"))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getKbFile(workspaceSlug: string, projectId: string, path: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `kb/file/?path=${encodeURIComponent(path)}`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  getKbFileRawUrl(workspaceSlug: string, projectId: string, path: string): string {
    return `${API_BASE_URL}${this.fundingUrl(workspaceSlug, projectId, `kb/file/raw/?path=${encodeURIComponent(path)}`)}`;
  }

  /**
   * Trigger a browser download of a ZIP archive of the opportunity's KB folder.
   * Uses fetch + blob so the browser ships its session cookie (credentials:
   * "include") rather than relying on the AchatPublic-style anonymous link.
   * Filename is taken from the Content-Disposition header set by the API.
   */
  async downloadKbAsZip(workspaceSlug: string, projectId: string, oppId: string): Promise<void> {
    const url = `${API_BASE_URL}${this.fundingUrl(workspaceSlug, projectId, `${oppId}/kb/download-zip/`)}`;
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) {
      let message = `Download failed (${response.status})`;
      try {
        const data = await response.json();
        if (data?.error) message = data.error;
      } catch {
        // body was not JSON; keep default message
      }
      throw new Error(message);
    }

    const disposition = response.headers.get("content-disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
    const filename = filenameMatch ? filenameMatch[1] : `${oppId}.zip`;

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  }

  async searchKb(workspaceSlug: string, projectId: string, query: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `kb/search/?q=${encodeURIComponent(query)}`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getKbProjects(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "kb/projects/"))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Proposals
  async getProposals(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createProposal(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateProposal(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async deleteProposal(workspaceSlug: string, projectId: string, oppId: string, pk: string): Promise<any> {
    return this.delete(this.fundingUrl(workspaceSlug, projectId, `${oppId}/proposals/${pk}/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Partners
  async getPartners(workspaceSlug: string): Promise<any> {
    return this.get(`/api/funding/workspaces/${workspaceSlug}/funding/partners/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createPartner(workspaceSlug: string, data: any): Promise<any> {
    return this.post(`/api/funding/workspaces/${workspaceSlug}/funding/partners/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Consortium
  async getConsortium(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/consortium/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async addConsortiumMember(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/consortium/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Meetings
  async getMeetings(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createMeeting(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateMeeting(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/meetings/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Milestones
  async getMilestones(workspaceSlug: string, projectId: string, oppId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createMilestone(workspaceSlug: string, projectId: string, oppId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateMilestone(workspaceSlug: string, projectId: string, oppId: string, pk: string, data: any): Promise<any> {
    return this.patch(this.fundingUrl(workspaceSlug, projectId, `${oppId}/milestones/${pk}/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // Create linked task in TASK project
  async createLinkedTask(workspaceSlug: string, projectId: string, issueId: string, data: any): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, `create-task/${issueId}/`), data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  // AI Chat (claude CLI backend)
  async listChatSessions(workspaceSlug: string, projectId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, "chat/sessions/"))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createChatSession(workspaceSlug: string, projectId: string, title?: string): Promise<any> {
    return this.post(this.fundingUrl(workspaceSlug, projectId, "chat/sessions/"), { title: title || "" })
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async listChatMessages(workspaceSlug: string, projectId: string, sessionId: string): Promise<any> {
    return this.get(this.fundingUrl(workspaceSlug, projectId, `chat/sessions/${sessionId}/messages/`))
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /**
   * POST a message and stream the assistant reply via SSE.
   *
   * Uses fetch + ReadableStream so we can send a body (EventSource is GET-only).
   * The handler is called once per parsed SSE `data:` event.
   */
  async streamChatMessage(
    workspaceSlug: string,
    projectId: string,
    sessionId: string,
    message: string,
    onEvent: (e: any) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const url = `${API_BASE_URL}${this.fundingUrl(workspaceSlug, projectId, `chat/sessions/${sessionId}/messages/`)}`;
    const csrfToken = (typeof document !== "undefined" ? document.cookie.match(/csrftoken=([^;]+)/) : null)?.[1];
    const res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: JSON.stringify({ message }),
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`chat failed: ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        try {
          onEvent(JSON.parse(line.slice(5).trim()));
        } catch {
          // ignore malformed event
        }
      }
    }
  }
}
