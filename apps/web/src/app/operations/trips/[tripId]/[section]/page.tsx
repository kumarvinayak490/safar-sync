import type { ReactElement } from "react";

import BookingsPage from "@/app/bookings/workspace-page";
import CommunicationsPage from "@/app/communications/workspace-page";
import ExportsPage from "@/app/exports/workspace-page";
import LaunchPage from "@/app/launch/workspace-page";
import OverviewPage from "@/app/overview/workspace-page";
import PaymentsPage from "@/app/payments/workspace-page";
import TripProfilePage from "@/app/trip-profile/workspace-page";
import TravelersPage from "@/app/travelers/workspace-page";
import {
  loadTripWorkspace,
  type TripWorkspaceRouteContext,
} from "@/app/workspace";
import type { TripWorkspaceSection } from "@/lib/operations-workspace";

type TripWorkspaceSectionPageProps = {
  params: {
    tripId: string;
    section: string;
  };
};

const SECTION_PAGES = {
  overview: OverviewPage,
  "trip-profile": TripProfilePage,
  launch: LaunchPage,
  bookings: BookingsPage,
  payments: PaymentsPage,
  travelers: TravelersPage,
  communications: CommunicationsPage,
  exports: ExportsPage,
} satisfies Record<
  TripWorkspaceSection,
  (context: TripWorkspaceRouteContext) => Promise<ReactElement>
>;

export const metadata = {
  title: "Trip Workspace | TripOS",
  description: "TripOS private Trip workspace",
};

export default async function TripWorkspaceSectionPage({
  params,
}: TripWorkspaceSectionPageProps) {
  const context = await loadTripWorkspace(params);
  const Page = SECTION_PAGES[context.section];

  return Page(context);
}
