import { observer } from "mobx-react";
import { PageHead } from "@/components/core/page-title";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { FundingDashboardView } from "@/plane-web/components/funding/dashboard";

function FundingDashboardPage() {
  const { currentWorkspace } = useWorkspace();
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - Funding Dashboard` : undefined;

  return (
    <>
      <PageHead title={pageTitle} />
      <FundingDashboardView />
    </>
  );
}

export default observer(FundingDashboardPage);
