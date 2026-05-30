import type { AuthSessionPayload } from "./auth-routing.ts";
import type { WorkspaceTrip } from "./workspace.ts";

export type OperationsWorkspaceContext = {
  organizer: NonNullable<AuthSessionPayload["onboarding"]["organizer"]>;
  roleLabel: string;
  selectedTrip: WorkspaceTrip | null;
  trips: WorkspaceTrip[];
};

export const ORGANIZER_NAV_ITEMS = [
  { label: "Home", path: "/home" },
  { label: "Organizer Identity", path: "/organizer-identity" },
  { label: "Team Access", path: "/team-access" },
  { label: "Payment Setup", path: "/payment-setup" },
  { label: "Trips", path: "/trips" },
] as const;

export const TRIP_WORKSPACE_NAV_ITEMS = [
  { label: "Overview", path: "/overview", section: "overview" },
  { label: "Trip Profile", path: "/trip-profile", section: "trip-profile" },
  { label: "Launch", path: "/launch", section: "launch" },
  { label: "Bookings", path: "/bookings", section: "bookings" },
  { label: "Payments", path: "/payments", section: "payments" },
  { label: "Travelers", path: "/travelers", section: "travelers" },
  {
    label: "Communications",
    path: "/communications",
    section: "communications",
  },
  { label: "Exports", path: "/exports", section: "exports" },
] as const;

export const TRIP_WORKSPACE_BASE_PATH = "/operations/trips" as const;

export type OrganizerNavPath = (typeof ORGANIZER_NAV_ITEMS)[number]["path"];
export type TripWorkspaceNavPath =
  (typeof TRIP_WORKSPACE_NAV_ITEMS)[number]["path"];
export type TripWorkspaceSection =
  (typeof TRIP_WORKSPACE_NAV_ITEMS)[number]["section"];

export type OperationsNavLink = {
  label: string;
  path: OrganizerNavPath | TripWorkspaceNavPath;
  href: string;
  active: boolean;
  disabled: boolean;
  disabledReason: string;
};

export type OperationsNavigation = {
  organizerNav: OperationsNavLink[];
  tripNav: OperationsNavLink[];
  isTripWorkspaceRoute: boolean;
  showTripWorkspaceNav: boolean;
  activeOrganizerLabel: string;
  activeTripLabel: string;
};

export type OperationsShellProps = {
  activePath: string;
  currentPath: string;
  navigation: OperationsNavigation;
  organizerId: number;
  organizerName: string;
  roleLabel: string;
  selectedTrip: WorkspaceTrip | null;
  trips: WorkspaceTrip[];
};

export function parseTripWorkspaceTripId(rawTripId: string): number | null {
  if (!/^[1-9]\d*$/.test(rawTripId)) {
    return null;
  }

  const tripId = Number(rawTripId);
  if (!Number.isSafeInteger(tripId)) {
    return null;
  }

  return tripId;
}

export function resolveTripWorkspaceSelectedTrip(
  trips: WorkspaceTrip[],
  tripId: number,
): WorkspaceTrip | null {
  return trips.find((trip) => trip.id === tripId) ?? null;
}

export function operationsHref(
  path: string,
  selectedTrip: WorkspaceTrip | null,
): string {
  if (!isTripWorkspacePath(path)) {
    return path;
  }

  if (!selectedTrip) {
    return "/trips";
  }

  return tripWorkspaceHref(path, selectedTrip.id);
}

export function tripWorkspaceHref(
  path: TripWorkspaceNavPath,
  tripId: number,
): string {
  return `${TRIP_WORKSPACE_BASE_PATH}/${tripId}${path}`;
}

export function tripWorkspaceCurrentPath(
  tripId: number,
  section: TripWorkspaceSection,
): string {
  return tripWorkspaceHref(tripWorkspaceSectionPath(section), tripId);
}

export function canCreateTrips(
  workspace: Pick<OperationsWorkspaceContext, "organizer">,
): boolean {
  return workspace.organizer.membership_role === "owner";
}

export function isTripWorkspacePath(
  path: string,
): path is TripWorkspaceNavPath {
  return TRIP_WORKSPACE_NAV_ITEMS.some((item) => item.path === path);
}

export function isTripWorkspaceSection(
  section: string,
): section is TripWorkspaceSection {
  return TRIP_WORKSPACE_NAV_ITEMS.some((item) => item.section === section);
}

export function tripWorkspaceSectionPath(
  section: TripWorkspaceSection,
): TripWorkspaceNavPath {
  return `/${section}` as TripWorkspaceNavPath;
}

export function buildOperationsNavigation(
  workspace: OperationsWorkspaceContext,
  paths: { activePath: string; currentPath: string },
): OperationsNavigation {
  const isTripWorkspaceRoute = isTripWorkspacePath(paths.activePath);
  const showTripWorkspaceNav = isTripWorkspaceRoute && !!workspace.selectedTrip;
  const activeOrganizerLabel =
    ORGANIZER_NAV_ITEMS.find((item) => item.path === paths.activePath)?.label ??
    "Organizer";
  const activeTripLabel =
    TRIP_WORKSPACE_NAV_ITEMS.find((item) => item.path === paths.activePath)
      ?.label ?? "Trip workspace";

  return {
    organizerNav: ORGANIZER_NAV_ITEMS.map((item) => ({
      ...item,
      href: item.path,
      active: !isTripWorkspaceRoute && item.path === paths.activePath,
      disabled: false,
      disabledReason: "",
    })),
    tripNav: showTripWorkspaceNav
      ? TRIP_WORKSPACE_NAV_ITEMS.map((item) => ({
          ...item,
          href: operationsHref(item.path, workspace.selectedTrip),
          active: item.path === paths.activePath,
          disabled: false,
          disabledReason: "",
        }))
      : [],
    isTripWorkspaceRoute,
    showTripWorkspaceNav,
    activeOrganizerLabel,
    activeTripLabel,
  };
}

export function buildOperationsShellProps(
  workspace: OperationsWorkspaceContext,
  paths: { activePath: string; currentPath: string },
): OperationsShellProps {
  return {
    activePath: paths.activePath,
    currentPath: paths.currentPath,
    navigation: buildOperationsNavigation(workspace, paths),
    organizerId: workspace.organizer.id,
    organizerName: workspace.organizer.name,
    roleLabel: workspace.roleLabel,
    selectedTrip: workspace.selectedTrip,
    trips: workspace.trips,
  };
}
