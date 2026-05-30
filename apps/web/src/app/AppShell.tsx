import Link from "next/link";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  ArrowRightLeft,
  CalendarDays,
  Compass,
  CreditCard,
  Download,
  FileText,
  House,
  Map,
  MessageSquare,
  Rocket,
  Route,
  TicketCheck,
  UsersRound,
  Eye,
  type LucideIcon,
} from "lucide-react";

import { publishPublicTripPageAction } from "@/app/launch/actions";
import { Badge } from "@/components/ui/badge";
import { FormSubmitButton } from "@/components/ui/form-submit-button";
import {
  operationsHref,
  type OperationsNavigation,
} from "@/lib/operations-workspace";
import { cn } from "@/lib/utils";
import {
  isPublicTripPagePublished,
  publicTripPagePublishDisabledReason,
  type WorkspaceTrip,
} from "@/lib/workspace";

export type AppShellProps = {
  activePath: string;
  children: ReactNode;
  currentPath: string;
  navigation: OperationsNavigation;
  organizerId: number;
  organizerName: string;
  roleLabel: string;
  selectedTrip: WorkspaceTrip | null;
  trips: WorkspaceTrip[];
};

const NAV_ICONS: Record<string, LucideIcon> = {
  "/home": House,
  "/organizer-identity": Compass,
  "/team-access": UsersRound,
  "/payment-setup": CreditCard,
  "/trips": Map,
  "/overview": Route,
  "/trip-profile": FileText,
  "/launch": Rocket,
  "/bookings": TicketCheck,
  "/payments": CreditCard,
  "/travelers": UsersRound,
  "/communications": MessageSquare,
  "/exports": Download,
};

export function AppShell({
  activePath,
  children,
  currentPath,
  navigation,
  organizerId,
  organizerName,
  roleLabel,
  selectedTrip,
  trips,
}: AppShellProps) {
  const isTripWorkspaceRoute = navigation.isTripWorkspaceRoute;
  const activeLayerLabel = isTripWorkspaceRoute
    ? "Trip workspace"
    : "Organizer layer";
  const activeRouteLabel = isTripWorkspaceRoute
    ? navigation.activeTripLabel
    : navigation.activeOrganizerLabel;
  const workbenchTitle = isTripWorkspaceRoute
    ? (selectedTrip?.title ?? "No Trip selected")
    : organizerWorkbenchTitle(activePath);

  if (isTripWorkspaceRoute && selectedTrip && navigation.showTripWorkspaceNav) {
    return (
      <main className="trip-workspace-shell">
        <TripControlRoomFrame
          activePath={activePath}
          currentPath={currentPath}
          navigation={navigation}
          organizerId={organizerId}
          roleLabel={roleLabel}
          selectedTrip={selectedTrip}
          trips={trips}
        >
          {children}
        </TripControlRoomFrame>
      </main>
    );
  }

  return (
    <main className="product-shell">
      <aside
        className="product-sidebar authenticated-rail"
        aria-label="TripOS navigation"
      >
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <Compass />
          </div>
          <div>
            <span>TripOS</span>
            <strong>{organizerName}</strong>
          </div>
        </div>
        <div className="product-nav-section">
          <span className="product-nav-label">Organizer</span>
          <nav
            className="product-nav authenticated-nav"
            aria-label="Organizer navigation"
          >
            {navigation.organizerNav.map((item) => {
              const Icon = NAV_ICONS[item.path];

              return (
                <Link
                  aria-current={item.active ? "page" : undefined}
                  className={cn("group", item.active ? "is-active" : "")}
                  href={item.href}
                  key={item.path}
                >
                  <Icon aria-hidden="true" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="sidebar-route-card" aria-label="Selected route">
          <Route aria-hidden="true" />
          <div>
            <span>{activeLayerLabel}</span>
            <strong>
              {isTripWorkspaceRoute && selectedTrip
                ? `${activeRouteLabel}: ${selectedTrip.title}`
                : activeRouteLabel}
            </strong>
          </div>
        </div>
      </aside>
      <section className="product-workbench">
        <header className="product-topbar">
          <div className="product-title-stack">
            <Badge variant="outline">{roleLabel}</Badge>
            <h1>{workbenchTitle}</h1>
          </div>
        </header>
        {children}
      </section>
    </main>
  );
}

function TripControlRoomFrame({
  activePath,
  children,
  currentPath,
  navigation,
  organizerId,
  roleLabel,
  selectedTrip,
  trips,
}: {
  activePath: string;
  children: ReactNode;
  currentPath: string;
  navigation: OperationsNavigation;
  organizerId: number;
  roleLabel: string;
  selectedTrip: WorkspaceTrip;
  trips: WorkspaceTrip[];
}) {
  const dateRange = formatTripDateRange(selectedTrip);
  const statusTone =
    selectedTrip.launchReadiness.effectiveBookingAvailability === "open"
      ? "is-live"
      : selectedTrip.publicationState === "published"
        ? "is-published"
        : "is-draft";
  const reservedSeats = Math.max(
    selectedTrip.capacity - selectedTrip.availableSeats,
    0,
  );
  const publicTripPagePublished = isPublicTripPagePublished(selectedTrip);
  const publishPublicTripPageDisabledReason =
    publicTripPagePublishDisabledReason({
      roleLabel,
      trip: selectedTrip,
    });
  const publishPublicTripPageDisabled =
    Boolean(publishPublicTripPageDisabledReason);

  return (
    <section className="trip-control-room" aria-label="Trip workspace">
      <aside
        className="trip-control-rail authenticated-rail"
        aria-label="Selected Trip navigation"
      >
        <div className="trip-control-trip-card">
          <Route aria-hidden="true" />
          <span>Selected Trip</span>
          <strong>{selectedTrip.title}</strong>
          <em>{dateRange}</em>
          {trips.length > 1 ? (
            <details className="trip-control-switcher">
              <summary>
                <ArrowRightLeft aria-hidden="true" />
                <span>Switch Trip</span>
              </summary>
              <div>
                {trips.map((trip) => (
                  <Link
                    aria-current={
                      trip.id === selectedTrip.id ? "page" : undefined
                    }
                    href={operationsHref(activePath, trip)}
                    key={trip.id}
                  >
                    {trip.title}
                  </Link>
                ))}
              </div>
            </details>
          ) : null}
        </div>

        <nav
          className="trip-control-links authenticated-nav"
          aria-label="Trip workspace navigation"
        >
          {navigation.tripNav.map((item) => {
            const Icon = NAV_ICONS[item.path];

            return (
              <Link
                aria-current={item.active ? "page" : undefined}
                className={cn(item.active ? "is-active" : "")}
                href={item.href}
                key={item.path}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="trip-control-escapes" aria-label="Exit Trip workspace">
          <Link className="trip-control-back" href="/trips">
            <ArrowLeft aria-hidden="true" />
            <span>Back to Trips</span>
          </Link>
          <Link className="trip-control-back" href="/home">
            <House aria-hidden="true" />
            <span>Home</span>
          </Link>
        </div>
      </aside>

      <div className="trip-control-stage">
        <header className="trip-control-header">
          <div className="trip-control-title">
            <div>
              <h1>{selectedTrip.title}</h1>
              <Badge className={statusTone} variant="outline">
                {
                  selectedTrip.launchReadiness
                    .effectiveBookingAvailabilityLabel
                }
              </Badge>
            </div>
            <p>
              <CalendarDays aria-hidden="true" />
              <span>{dateRange}</span>
              <span aria-hidden="true">•</span>
              <span>
                {reservedSeats}/{selectedTrip.capacity} seats reserved
              </span>
              <span aria-hidden="true">•</span>
              <span>{roleLabel}</span>
            </p>
          </div>
          <div className="trip-control-actions">
            {publicTripPagePublished ? (
              selectedTrip.publicUrlPath ? (
                <Link
                  className="trip-public-page-action"
                  href={selectedTrip.publicUrlPath}
                  target="_blank" 
                >
                  <Eye aria-hidden="true" />
                  <span>View Public Trip Page</span>
                </Link>
              ) : (
                <button
                  className="trip-public-page-action is-disabled"
                  disabled
                  title="Public page URL is not available yet."
                  type="button"
                >
                  <Eye aria-hidden="true" />
                  <span>Public Page Published</span>
                </button>
              )
            ) : (
              <form action={publishPublicTripPageAction}>
                <input name="organizerId" type="hidden" value={organizerId} />
                <input name="tripId" type="hidden" value={selectedTrip.id} />
                <input name="currentPath" type="hidden" value={currentPath} />
                <input
                  name="publishLockAcknowledged"
                  type="hidden"
                  value="on"
                />
                <FormSubmitButton
                  className="trip-public-page-action"
                  disabled={publishPublicTripPageDisabled}
                  pendingChildren={
                    <>
                      <Rocket aria-hidden="true" />
                      <span>Publishing...</span>
                    </>
                  }
                  title={publishPublicTripPageDisabledReason}
                >
                  <Rocket aria-hidden="true" />
                  <span>Publish Public Trip Page</span>
                </FormSubmitButton>
              </form>
            )}
          </div>
        </header>
        <div className="trip-control-content">{children}</div>
      </div>
    </section>
  );
}

function organizerWorkbenchTitle(activePath: string): string {
  switch (activePath) {
    case "/organizer-identity":
      return "Organizer Identity";
    case "/team-access":
      return "Team Access";
    case "/payment-setup":
      return "Payment Setup";
    case "/trips":
      return "Trips";
    default:
      return "Organizer Home";
  }
}

function formatTripDateRange(trip: WorkspaceTrip): string {
  if (!trip.startDate || !trip.endDate) {
    return "Dates pending";
  }

  const formatter = new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return `${formatter.format(new Date(`${trip.startDate}T00:00:00`))} to ${formatter.format(
    new Date(`${trip.endDate}T00:00:00`),
  )}`;
}
