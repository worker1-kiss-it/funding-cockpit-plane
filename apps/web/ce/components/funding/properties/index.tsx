import { useEffect, useState, useCallback } from "react";
import { observer } from "mobx-react";
import { Star, ExternalLink, FileText } from "lucide-react";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

interface FundingPropertiesProps {
  workItemId: string;
  projectId: string;
  workspaceSlug: string;
  isEditable: boolean;
}

export const FundingProperties = observer(function FundingProperties({
  workItemId,
  projectId,
  workspaceSlug,
  isEditable,
}: FundingPropertiesProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!workspaceSlug || !projectId || !workItemId) return;
    setLoading(true);
    // Fetch pipeline and find the opportunity for this issue
    service.getPipeline(workspaceSlug, projectId)
      .then((res) => {
        const opp = (res?.opportunities || []).find((o: any) => o.issue === workItemId);
        setData(opp || null);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [workspaceSlug, projectId, workItemId]);

  const handleUpdate = useCallback(async (field: string, value: any) => {
    if (!data?.id || !isEditable) return;
    try {
      const updated = await service.updateOpportunity(workspaceSlug, projectId, data.id, { [field]: value });
      setData((prev: any) => ({ ...prev, ...updated }));
    } catch {
      // silently fail
    }
  }, [data?.id, workspaceSlug, projectId, isEditable]);

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
            <button
              key={i}
              onClick={() => isEditable && handleUpdate("relevance", i)}
              className={`${isEditable ? "cursor-pointer hover:scale-110" : "cursor-default"} transition-transform`}
            >
              <Star
                className={`size-4 ${i <= (data.relevance || 0) ? "fill-yellow-400 text-yellow-400" : "text-custom-text-400"}`}
              />
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

      {/* External ID */}
      {data.external_id && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">ID</span>
          <span className="text-xs font-mono bg-custom-background-90 px-2 py-0.5 rounded">{data.external_id}</span>
        </div>
      )}

      {/* Type */}
      {data.opportunity_type && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Type</span>
          <span className="text-sm">{data.opportunity_type}</span>
        </div>
      )}

      {/* Source URL */}
      {data.url && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Source</span>
          <a href={data.url} target="_blank" rel="noopener noreferrer" className="text-sm text-custom-primary-100 hover:underline flex items-center gap-1">
            Link <ExternalLink className="size-3" />
          </a>
        </div>
      )}

      {/* Deadline */}
      {data.deadline && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-custom-text-300">Deadline</span>
          <span className="text-sm">{data.deadline}</span>
        </div>
      )}

      {/* Linked Docs */}
      {data.linked_docs?.length > 0 && (
        <div>
          <span className="text-sm text-custom-text-300 flex items-center gap-1 mb-1">
            <FileText className="size-3" /> Linked Docs ({data.linked_docs.length})
          </span>
          <div className="space-y-0.5">
            {data.linked_docs.slice(0, 5).map((doc: string, i: number) => (
              <div key={i} className="text-xs text-custom-text-200 truncate pl-4">{doc.split("/").pop()}</div>
            ))}
            {data.linked_docs.length > 5 && (
              <div className="text-xs text-custom-text-400 pl-4">+{data.linked_docs.length - 5} more</div>
            )}
          </div>
        </div>
      )}

      {/* Fit Notes */}
      {data.fit_notes && (
        <div>
          <span className="text-sm text-custom-text-300 mb-1 block">Fit Notes</span>
          <p className="text-xs text-custom-text-200 bg-custom-background-90 rounded p-2 whitespace-pre-wrap">{data.fit_notes}</p>
        </div>
      )}

      {/* Next Step */}
      {data.next_step && (
        <div>
          <span className="text-sm text-custom-text-300 mb-1 block">Next Step</span>
          <p className="text-xs text-custom-text-200">{data.next_step}</p>
        </div>
      )}
    </div>
  );
});
