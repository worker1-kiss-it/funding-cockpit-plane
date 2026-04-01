/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { FundingProperties } from "@/plane-web/components/funding/properties";

export type TWorkItemAdditionalSidebarProperties = {
  workItemId: string;
  workItemTypeId: string | null;
  projectId: string;
  workspaceSlug: string;
  isEditable: boolean;
  isPeekView?: boolean;
};

export function WorkItemAdditionalSidebarProperties(props: TWorkItemAdditionalSidebarProperties) {
  return (
    <FundingProperties
      workItemId={props.workItemId}
      projectId={props.projectId}
      workspaceSlug={props.workspaceSlug}
      isEditable={props.isEditable}
    />
  );
}
