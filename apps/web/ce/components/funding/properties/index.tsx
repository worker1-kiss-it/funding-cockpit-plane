import { useEffect, useState, useCallback } from "react";
import { observer } from "mobx-react";
import {
  Star, ExternalLink, FileText, ChevronDown, Plus, Calendar,
  Users, FileCheck, Milestone, Trash2, Clock
} from "lucide-react";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

interface FundingPropertiesProps {
  workItemId: string;
  projectId: string;
  workspaceSlug: string;
  isEditable: boolean;
}

// Collapsible section wrapper
const Section = ({ title, icon: Icon, count, children, defaultOpen = false }: {
  title: string; icon: any; count?: number; children: React.ReactNode; defaultOpen?: boolean;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-custom-border-200 pt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center justify-between w-full py-1 text-xs font-medium text-custom-text-300 uppercase tracking-wider hover:text-custom-text-100">
        <span className="flex items-center gap-1.5">
          <Icon className="size-3.5" />
          {title} {count !== undefined && <span className="text-custom-text-400">({count})</span>}
        </span>
        <ChevronDown className={`size-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="mt-2 space-y-2">{children}</div>}
    </div>
  );
};

export const FundingProperties = observer(function FundingProperties({
  workItemId, projectId, workspaceSlug, isEditable,
}: FundingPropertiesProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [proposals, setProposals] = useState<any[]>([]);
  const [meetings, setMeetings] = useState<any[]>([]);
  const [milestones, setMilestones] = useState<any[]>([]);
  const [consortium, setConsortium] = useState<any[]>([]);

  useEffect(() => {
    if (!workspaceSlug || !projectId || !workItemId) return;
    setLoading(true);
    service.getPipeline(workspaceSlug, projectId)
      .then((res) => {
        const opp = (res?.opportunities || []).find((o: any) => o.issue === workItemId);
        setData(opp || null);
        if (opp?.id) {
          // Load related data
          service.getProposals(workspaceSlug, projectId, opp.id).then(setProposals).catch(() => {});
          service.getMeetings(workspaceSlug, projectId, opp.id).then(setMeetings).catch(() => {});
          service.getMilestones(workspaceSlug, projectId, opp.id).then(setMilestones).catch(() => {});
          service.getConsortium(workspaceSlug, projectId, opp.id).then(setConsortium).catch(() => {});
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [workspaceSlug, projectId, workItemId]);

  const handleUpdate = useCallback(async (field: string, value: any) => {
    if (!data?.id || !isEditable) return;
    try {
      const updated = await service.updateOpportunity(workspaceSlug, projectId, data.id, { [field]: value });
      setData((prev: any) => ({ ...prev, ...updated }));
    } catch { /* silently fail */ }
  }, [data?.id, workspaceSlug, projectId, isEditable]);

  // Quick-add handlers
  const addProposal = async () => {
    if (!data?.id) return;
    const title = prompt("Proposal title:");
    if (!title) return;
    try {
      const created = await service.createProposal(workspaceSlug, projectId, data.id, { title, status: "draft" });
      setProposals((prev) => [created, ...prev]);
    } catch { /* silently fail */ }
  };

  const addMeeting = async () => {
    if (!data?.id) return;
    const title = prompt("Meeting title:");
    if (!title) return;
    try {
      const created = await service.createMeeting(workspaceSlug, projectId, data.id, {
        title, date: new Date().toISOString(), meeting_type: "internal",
      });
      setMeetings((prev) => [created, ...prev]);
    } catch { /* silently fail */ }
  };

  const addMilestone = async () => {
    if (!data?.id) return;
    const title = prompt("Milestone title:");
    if (!title) return;
    try {
      const created = await service.createMilestone(workspaceSlug, projectId, data.id, {
        title, status: "pending",
      });
      setMilestones((prev) => [...prev, created]);
    } catch { /* silently fail */ }
  };

  const statusColors: Record<string, string> = {
    draft: "bg-gray-500/10 text-gray-400",
    internal_review: "bg-yellow-500/10 text-yellow-500",
    submitted: "bg-blue-500/10 text-blue-500",
    revision_requested: "bg-orange-500/10 text-orange-500",
    accepted: "bg-green-500/10 text-green-500",
    rejected: "bg-red-500/10 text-red-500",
    pending: "bg-gray-500/10 text-gray-400",
    in_progress: "bg-blue-500/10 text-blue-500",
    completed: "bg-green-500/10 text-green-500",
    delayed: "bg-red-500/10 text-red-500",
  };

  if (loading) return null;
  if (!data) return null;

  return (
    <div className="space-y-3 pt-3 border-t border-custom-border-200">
      <h4 className="text-xs font-medium text-custom-text-300 uppercase tracking-wider">Funding Details</h4>

      {/* Relevance */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-custom-text-300">Relevance</span>
        <div className="flex items-center gap-0.5">
          {[1, 2, 3, 4, 5].map((i) => (
            <button key={i} onClick={() => isEditable && handleUpdate("relevance", i)}
              className={`${isEditable ? "cursor-pointer hover:scale-110" : "cursor-default"} transition-transform`}>
              <Star className={`size-4 ${i <= (data.relevance || 0) ? "fill-yellow-400 text-yellow-400" : "text-custom-text-400"}`} />
            </button>
          ))}
        </div>
      </div>

      {/* Budget */}
      {data.budget && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Budget</span>
          <span className="text-sm font-medium">{data.budget}</span>
        </div>
      )}

      {/* ID + Type */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-custom-text-300">ID</span>
        <span className="text-xs font-mono bg-custom-background-90 px-2 py-0.5 rounded">{data.external_id}</span>
      </div>
      {data.opportunity_type && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Type</span>
          <span className="text-sm">{data.opportunity_type}</span>
        </div>
      )}

      {/* URL + Deadline */}
      {data.url && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Source</span>
          <a href={data.url} target="_blank" rel="noopener noreferrer" className="text-sm text-custom-primary-100 hover:underline flex items-center gap-1">
            Link <ExternalLink className="size-3" />
          </a>
        </div>
      )}
      {data.deadline && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Deadline</span>
          <span className="text-sm">{data.deadline}</span>
        </div>
      )}

      {/* Fit Notes */}
      {data.fit_notes && (
        <div>
          <span className="text-sm text-custom-text-300 mb-1 block">Fit Notes</span>
          <p className="text-xs text-custom-text-200 bg-custom-background-90 rounded p-2 whitespace-pre-wrap max-h-24 overflow-auto">{data.fit_notes}</p>
        </div>
      )}

      {/* Next Step */}
      {data.next_step && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Next Step</span>
          <span className="text-xs text-custom-text-200">{data.next_step}</span>
        </div>
      )}

      {/* Linked Docs */}
      {data.linked_docs?.length > 0 && (
        <Section title="Linked Docs" icon={FileText} count={data.linked_docs.length}>
          <div className="space-y-0.5">
            {data.linked_docs.map((doc: string, i: number) => (
              <div key={i} className="text-xs text-custom-text-200 truncate py-0.5 px-1 rounded hover:bg-custom-background-90">
                {doc.split("/").pop()}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Proposals */}
      <Section title="Proposals" icon={FileCheck} count={proposals.length}>
        {proposals.map((p: any) => (
          <div key={p.id} className="flex items-center justify-between py-1 px-2 rounded bg-custom-background-90 text-xs">
            <div className="truncate flex-1">
              <span className="font-medium">{p.title}</span>
              <span className="text-custom-text-400 ml-1">{p.version}</span>
            </div>
            <span className={`px-1.5 py-0.5 rounded text-[10px] ${statusColors[p.status] || ""}`}>{p.status}</span>
          </div>
        ))}
        {isEditable && (
          <button onClick={addProposal} className="flex items-center gap-1 text-xs text-custom-primary-100 hover:underline">
            <Plus className="size-3" /> Add proposal
          </button>
        )}
      </Section>

      {/* Consortium */}
      <Section title="Consortium" icon={Users} count={consortium.length}>
        {consortium.map((c: any) => (
          <div key={c.id} className="flex items-center justify-between py-1 px-2 rounded bg-custom-background-90 text-xs">
            <div className="truncate">
              <span className="font-medium">{c.partner_name}</span>
              {c.partner_country && <span className="text-custom-text-400 ml-1">({c.partner_country})</span>}
            </div>
            <span className="text-custom-text-400">{c.role}</span>
          </div>
        ))}
        {consortium.length === 0 && <div className="text-xs text-custom-text-400">No consortium members</div>}
      </Section>

      {/* Meetings */}
      <Section title="Meetings" icon={Calendar} count={meetings.length}>
        {meetings.slice(0, 5).map((m: any) => (
          <div key={m.id} className="py-1 px-2 rounded bg-custom-background-90 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium truncate">{m.title}</span>
              <span className="text-custom-text-400 shrink-0 ml-2">{m.meeting_type}</span>
            </div>
            <div className="flex items-center gap-1 text-custom-text-400 mt-0.5">
              <Clock className="size-2.5" />
              {m.date ? new Date(m.date).toLocaleDateString() : "No date"}
            </div>
          </div>
        ))}
        {isEditable && (
          <button onClick={addMeeting} className="flex items-center gap-1 text-xs text-custom-primary-100 hover:underline">
            <Plus className="size-3" /> Add meeting
          </button>
        )}
      </Section>

      {/* Milestones */}
      <Section title="Milestones" icon={Milestone} count={milestones.length}>
        {milestones.map((ms: any) => (
          <div key={ms.id} className="flex items-center justify-between py-1 px-2 rounded bg-custom-background-90 text-xs">
            <div className="truncate flex-1">
              <span className="font-medium">{ms.title}</span>
              {ms.due_date && <span className="text-custom-text-400 ml-1">due {ms.due_date}</span>}
            </div>
            <span className={`px-1.5 py-0.5 rounded text-[10px] ${statusColors[ms.status] || ""}`}>{ms.status}</span>
          </div>
        ))}
        {isEditable && (
          <button onClick={addMilestone} className="flex items-center gap-1 text-xs text-custom-primary-100 hover:underline">
            <Plus className="size-3" /> Add milestone
          </button>
        )}
      </Section>
    </div>
  );
});
