/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { layout, route } from "@react-router/dev/routes";
import type { RouteConfigEntry } from "@react-router/dev/routes";

export const extendedRoutes: RouteConfigEntry[] = [
  // Merge into the ALL > WORKSPACE > PROJECTS layout hierarchy
  layout("./(all)/layout.tsx", [
    layout("./(all)/[workspaceSlug]/layout.tsx", [
      layout("./(all)/[workspaceSlug]/(projects)/layout.tsx", [
        // Funding Dashboard
        layout("./(all)/[workspaceSlug]/(projects)/funding-dashboard/layout.tsx", [
          route(":workspaceSlug/funding-dashboard", "./(all)/[workspaceSlug]/(projects)/funding-dashboard/page.tsx"),
        ]),
        // Knowledge Base
        layout("./(all)/[workspaceSlug]/(projects)/knowledge-base/layout.tsx", [
          route(":workspaceSlug/knowledge-base", "./(all)/[workspaceSlug]/(projects)/knowledge-base/page.tsx"),
        ]),
      ]),
    ]),
  ]),
];
