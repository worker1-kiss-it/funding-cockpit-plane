import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { BarChart3, AlertTriangle, Calendar, TrendingUp, Target } from "lucide-react";
import { useProject } from "@/hooks/store/use-project";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

export const FundingDashboardView = observer(function FundingDashboardView() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const { workspaceProjectIds } = useProject();
  const [stats, setStats] = useState<any>(null);
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const projectId = workspaceProjectIds?.[0];

  useEffect(() => {
    if (!workspaceSlug || !projectId) return;
    setLoading(true);
    Promise.all([
      service.getDashboard(workspaceSlug, projectId).catch(() => null),
      service.getDeadlines(workspaceSlug, projectId).catch(() => ({ deadlines: [] })),
    ]).then(([dashData, dlData]) => {
      setStats(dashData);
      setDeadlines(dlData?.deadlines || []);
      setLoading(false);
    });
  }, [workspaceSlug, projectId]);

  if (!projectId) {
    return <div className="flex items-center justify-center h-full text-custom-text-300">No project found. Create a project first.</div>;
  }

  if (loading) {
    return <div className="flex items-center justify-center h-full text-custom-text-300">Loading dashboard...</div>;
  }

  const statCards = [
    { label: "Total Opportunities", value: stats?.total_opportunities || 0, icon: BarChart3, color: "text-custom-primary-100" },
    { label: "High Priority", value: stats?.high_priority || 0, icon: Target, color: "text-orange-500" },
    { label: "Deadlines This Month", value: stats?.deadlines_this_month || 0, icon: Calendar, color: "text-yellow-500" },
    { label: "Urgent (< 7 days)", value: stats?.urgent_deadlines || 0, icon: AlertTriangle, color: "text-red-500" },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="rounded-lg border border-custom-border-200 bg-custom-background-100 p-5">
            <div className="flex items-center gap-3">
              <card.icon className={`size-5 ${card.color}`} />
              <span className="text-sm text-custom-text-300">{card.label}</span>
            </div>
            <div className={`text-3xl font-bold mt-2 ${card.color}`}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Phase Distribution */}
      {stats?.by_phase && (
        <div className="rounded-lg border border-custom-border-200 bg-custom-background-100 p-5">
          <h3 className="text-base font-medium mb-4">By Phase</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.by_phase).map(([phase, count]) => (
              <div key={phase} className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-custom-background-90 text-sm">
                <span className="text-custom-text-300">{phase}:</span>
                <span className="font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Deadlines */}
      <div className="rounded-lg border border-custom-border-200 bg-custom-background-100 p-5">
        <h3 className="text-base font-medium mb-4">Upcoming Deadlines</h3>
        <div className="space-y-2">
          {deadlines.slice(0, 15).map((dl: any) => (
            <div key={dl.id} className="flex items-center justify-between py-2.5 px-4 rounded-md bg-custom-background-90">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{dl.name}</div>
                <div className="text-xs text-custom-text-300">{dl.opportunity_type} &middot; {dl.budget}</div>
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-4">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  dl.urgency === "red" ? "bg-red-500/10 text-red-500" :
                  dl.urgency === "yellow" ? "bg-yellow-500/10 text-yellow-500" :
                  "bg-green-500/10 text-green-500"
                }`}>
                  {dl.days_left}d
                </span>
                <span className="text-sm text-custom-text-300">{dl.deadline}</span>
              </div>
            </div>
          ))}
          {deadlines.length === 0 && (
            <div className="text-center py-8 text-custom-text-300 text-sm">No upcoming deadlines</div>
          )}
        </div>
      </div>
    </div>
  );
});
