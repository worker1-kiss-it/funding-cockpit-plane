/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// store
import { CoreRootStore } from "@/store/root.store";
import type { ITimelineStore } from "./timeline";
import { TimeLineStore } from "./timeline";
import type { IFundingStore } from "./funding";
import { FundingStore } from "./funding";

export class RootStore extends CoreRootStore {
  timelineStore: ITimelineStore;
  fundingStore: IFundingStore;

  constructor() {
    super();

    this.timelineStore = new TimeLineStore(this);
    this.fundingStore = new FundingStore(this);
  }
}
