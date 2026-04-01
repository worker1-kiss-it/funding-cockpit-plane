/**
 * Additional widget action buttons for funding cockpit.
 * Adds a "Create Task" button next to "Add sub-work item", "Add relation", etc.
 */

import { ListTodo } from "lucide-react";
import { Button } from "@plane/propel/button";
// plane types
import type { TIssueServiceType, TWorkItemWidgets } from "@plane/types";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

export type TWorkItemAdditionalWidgetActionButtonsProps = {
  disabled: boolean;
  hideWidgets: TWorkItemWidgets[];
  issueServiceType: TIssueServiceType;
  projectId: string;
  workItemId: string;
  workspaceSlug: string;
};

export function WorkItemAdditionalWidgetActionButtons(props: TWorkItemAdditionalWidgetActionButtonsProps) {
  const { disabled, workspaceSlug, projectId, workItemId } = props;

  const handleCreateTask = async () => {
    const name = prompt("Task name:");
    if (!name?.trim()) return;
    try {
      await service.createLinkedTask(workspaceSlug, projectId, workItemId, { name: name.trim() });
      alert(`Task "${name.trim()}" created in Funding Tasks project with relation.`);
    } catch {
      alert("Failed to create task.");
    }
  };

  return (
    <Button variant="secondary" disabled={disabled} size="lg" onClick={handleCreateTask}>
      <ListTodo className="h-3.5 w-3.5 flex-shrink-0" strokeWidth={2} />
      <span className="text-body-xs-medium">Create task</span>
    </Button>
  );
}
