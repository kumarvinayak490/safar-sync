import { notFound, redirect } from "next/navigation";

import { currentSession } from "@/lib/auth";
import { rootRedirectFromSession } from "@/lib/auth-routing";
import {
  isTripWorkspaceSection,
  parseTripWorkspaceTripId,
  resolveTripWorkspaceSelectedTrip,
  tripWorkspaceCurrentPath,
  tripWorkspaceSectionPath,
  type OperationsWorkspaceContext,
  type TripWorkspaceNavPath,
  type TripWorkspaceSection,
} from "@/lib/operations-workspace";
import { getWorkspaceTrips } from "@/lib/workspace";

export type TripWorkspaceRouteContext = {
  activePath: TripWorkspaceNavPath;
  currentPath: string;
  section: TripWorkspaceSection;
  workspace: OperationsWorkspaceContext & {
    selectedTrip: NonNullable<OperationsWorkspaceContext["selectedTrip"]>;
  };
};

export async function loadWorkspace(): Promise<OperationsWorkspaceContext> {
  const { organizer, trips } = await loadOrganizerWorkspaceBase();

  return {
    organizer,
    roleLabel: organizer.membership_label,
    selectedTrip: null,
    trips,
  };
}

export async function loadTripWorkspace({
  section,
  tripId: rawTripId,
}: {
  section: string;
  tripId: string;
}): Promise<TripWorkspaceRouteContext> {
  const tripId = parseTripWorkspaceTripId(rawTripId);
  if (!tripId || !isTripWorkspaceSection(section)) {
    notFound();
  }

  const { organizer, trips } = await loadOrganizerWorkspaceBase();
  const selectedTrip = resolveTripWorkspaceSelectedTrip(trips, tripId);

  if (!selectedTrip) {
    notFound();
  }

  return {
    activePath: tripWorkspaceSectionPath(section),
    currentPath: tripWorkspaceCurrentPath(tripId, section),
    section,
    workspace: {
      organizer,
      roleLabel: organizer.membership_label,
      selectedTrip,
      trips,
    },
  };
}

async function loadOrganizerWorkspaceBase() {
  const session = await currentSession();

  if (!session?.authenticated || session.onboarding.state === "no_organizer") {
    redirect(rootRedirectFromSession(session));
  }

  const organizer = session.onboarding.organizer;
  if (!organizer) {
    redirect("/onboarding/organizer");
  }

  const trips = await getWorkspaceTrips(organizer.id);

  return {
    organizer,
    trips,
  };
}
