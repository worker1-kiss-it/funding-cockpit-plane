/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useNavigate, useParams } from "react-router";
// components
import { useTranslation } from "@plane/i18n";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { PageHead } from "@/components/core/page-title";
import { WorkspaceHomeView } from "@/components/home";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useProject } from "@/hooks/store/use-project";
// local components
import { WorkspaceDashboardHeader } from "./header";

function WorkspaceDashboardPage() {
  const { currentWorkspace } = useWorkspace();
  const { workspaceProjectIds, getProjectById } = useProject();
  const { workspaceSlug } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // Auto-redirect to the first project's board view (funding pipeline)
  useEffect(() => {
    if (workspaceProjectIds && workspaceProjectIds.length > 0 && workspaceSlug) {
      const firstProjectId = workspaceProjectIds[0];
      const project = getProjectById(firstProjectId);
      if (project?.identifier === "FUND") {
        navigate(`/${workspaceSlug}/projects/${firstProjectId}/issues/`, { replace: true });
      }
    }
  }, [workspaceProjectIds, workspaceSlug, navigate, getProjectById]);

  // derived values
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace?.name} - ${t("home.title")}` : undefined;

  return (
    <>
      <AppHeader header={<WorkspaceDashboardHeader />} />
      <ContentWrapper>
        <PageHead title={pageTitle} />
        <WorkspaceHomeView />
      </ContentWrapper>
    </>
  );
}

export default observer(WorkspaceDashboardPage);
