import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";

export default function FundingDashboardLayout() {
  return (
    <>
      <AppHeader
        header={
          <div className="flex items-center gap-2 px-5 py-2.5">
            <h3 className="text-lg font-semibold">Funding Dashboard</h3>
          </div>
        }
      />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
