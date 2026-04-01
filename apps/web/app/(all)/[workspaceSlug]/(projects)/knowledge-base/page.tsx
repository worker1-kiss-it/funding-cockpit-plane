import { observer } from "mobx-react";
import { PageHead } from "@/components/core/page-title";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { KnowledgeBaseView } from "@/plane-web/components/funding/kb";

function KnowledgeBasePage() {
  const { currentWorkspace } = useWorkspace();
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - Knowledge Base` : undefined;

  return (
    <>
      <PageHead title={pageTitle} />
      <KnowledgeBaseView />
    </>
  );
}

export default observer(KnowledgeBasePage);
