import { OperationsWorkspaceShell } from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildTripProfileShellModel,
  type TripProfileRole,
} from "@/lib/trip-profile";

import { TripProfileWorkspace } from "./TripProfileWorkspace";

export const metadata = {
  title: "Trip Profile | TripOS",
  description: "TripOS selected Trip Profile",
};

export default async function TripProfilePage({
  activePath,
  currentPath,
  workspace,
}: TripWorkspaceRouteContext) {
  const trip = workspace.selectedTrip;
  const role: TripProfileRole =
    workspace.organizer.membership_role === "owner" ? "owner" : "operator";
  const model = buildTripProfileShellModel({
    role,
    trip,
  });

  return (
    <OperationsWorkspaceShell
      activePath={activePath}
      currentPath={currentPath}
      workspace={workspace}
    >
      <TripProfileWorkspace
        model={model}
        organizerId={workspace.organizer.id}
      />
    </OperationsWorkspaceShell>
  );
}
