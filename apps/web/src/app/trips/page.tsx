import Link from "next/link";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  ListFilter,
  LockKeyhole,
  Plus,
  Search,
  TicketCheck,
} from "lucide-react";

import { OperationsWorkspaceShell } from "@/app/OperationsWorkspaceShell";
import { loadWorkspace } from "@/app/workspace";
import { canCreateTrips, operationsHref } from "@/lib/operations-workspace";
import type { WorkspaceTrip } from "@/lib/workspace";

export const metadata = {
  title: "Trips | TripOS",
  description: "Manage TripOS paid Trips",
};

export default async function TripsPage({
  searchParams,
}: {
  searchParams: {
    q?: string | string[];
    status?: string | string[];
  };
}) {
  const workspace = await loadWorkspace();
  const isOwner = canCreateTrips(workspace);
  const query = singleSearchParam(searchParams.q).trim();
  const statusFilter = normalizeStatusFilter(searchParams.status);
  const hasTrips = workspace.trips.length > 0;
  const filteredTrips = workspace.trips.filter((trip) =>
    tripMatchesFilters(trip, { query, statusFilter }),
  );
  const draftCount = workspace.trips.filter(
    (trip) => trip.publicationState !== "published",
  ).length;
  const openBookingCount = workspace.trips.filter(
    (trip) => trip.effectiveBookingAvailability === "open",
  ).length;

  return (
    <OperationsWorkspaceShell
      activePath="/trips"
      currentPath="/trips"
      workspace={workspace}
    >
      <section className="workspace-section trips-page">
        {hasTrips ? (
          <>
            <div className="workspace-heading trips-management-heading">
              <div>
                <p className="eyebrow">Trips</p>
                <h2>Trip list</h2>
                <p className="workspace-heading-copy">
                  {isOwner
                    ? "Create, find, and open Trips."
                    : "Open existing Trips."}
                </p>
              </div>
              {isOwner ? (
                <Link className="primary-link-button icon-link" href="/trips/new">
                  <Plus aria-hidden="true" />
                  Create Trip
                </Link>
              ) : (
                <span className="trips-readonly-note">
                  <LockKeyhole aria-hidden="true" />
                  Owner creates Trips
                </span>
              )}
            </div>

            <div className="trips-list-summary" aria-label="Trip list summary">
              <div>
                <span>Total Trips</span>
                <strong>{workspace.trips.length}</strong>
              </div>
              <div>
                <span>Draft pages</span>
                <strong>{draftCount}</strong>
              </div>
              <div>
                <span>Open booking</span>
                <strong>{openBookingCount}</strong>
              </div>
            </div>

            <form action="/trips" className="trips-toolbar">
              <label className="trips-search-field">
                <Search aria-hidden="true" />
                <span>Find Trip</span>
                <input
                  defaultValue={query}
                  name="q"
                  placeholder="Trip title"
                  type="search"
                />
              </label>
              <label className="trips-filter-field">
                <ListFilter aria-hidden="true" />
                <span>Filter</span>
                <select defaultValue={statusFilter} name="status">
                  <option value="all">All states</option>
                  <option value="published">Published page</option>
                  <option value="draft">Draft page</option>
                  <option value="open_booking">Open booking</option>
                  <option value="closed_booking">Closed booking</option>
                  <option value="sold_out">Sold out</option>
                </select>
              </label>
              <button className="secondary-link-button" type="submit">
                Apply
              </button>
              {query || statusFilter !== "all" ? (
                <Link className="settings-link compact-link" href="/trips">
                  Clear
                </Link>
              ) : null}
            </form>

            {filteredTrips.length ? (
              <div className="trips-management-list">
                {filteredTrips.map((trip) => (
                  <TripManagementRow key={trip.id} trip={trip} />
                ))}
              </div>
            ) : (
              <div className="empty-state standalone trips-empty-state">
                <span>No matching Trips</span>
                <strong>Adjust the list filters</strong>
                <p>No Trip matches this view.</p>
                <Link className="settings-link compact-link" href="/trips">
                  Clear filters
                </Link>
              </div>
            )}
          </>
        ) : (
          <div className="empty-state standalone trips-empty-state">
            <span>No Trips yet</span>
            <strong>
              {isOwner
                ? "Create the first Trip when ready"
                : "Waiting for an Owner"}
            </strong>
            <p>
              {isOwner
                ? "Draft setup is available now."
                : "An Owner must create the first Trip."}
            </p>
            {isOwner ? (
              <Link className="primary-link-button icon-link" href="/trips/new">
                <Plus aria-hidden="true" />
                Create Trip
              </Link>
            ) : (
              <span className="trips-readonly-note">
                <LockKeyhole aria-hidden="true" />
                Owner action required
              </span>
            )}
          </div>
        )}
      </section>
    </OperationsWorkspaceShell>
  );
}

function TripManagementRow({ trip }: { trip: WorkspaceTrip }) {
  const reservedSeats = Math.max(trip.capacity - trip.availableSeats, 0);

  return (
    <article className="trip-management-row">
      <div className="trip-row-main">
        <span>
          <CalendarDays aria-hidden="true" />
          {formatShortDate(trip.startDate)} to {formatShortDate(trip.endDate)}
        </span>
        <strong>{trip.title}</strong>
        <em>
          Open the private Trip workspace.
        </em>
      </div>
      <div className="trip-row-status">
        <span
          className={`status-chip ${publicationStatusClass(
            trip.publicationState,
          )}`}
        >
          {titleCase(trip.publicationState)} page
        </span>
        <span
          className={`status-chip ${bookingStatusClass(
            trip.effectiveBookingAvailability,
          )}`}
        >
          {titleCase(trip.effectiveBookingAvailability)} booking
        </span>
        <span className="status-chip is-readonly">
          <TicketCheck aria-hidden="true" />
          {reservedSeats}/{trip.capacity} reserved
        </span>
        {trip.launchReadiness.ready ? (
          <span className="trip-inline-state is-clear">
            <CheckCircle2 aria-hidden="true" />
            Launch clear
          </span>
        ) : (
          <span className="trip-inline-state is-blocked">
            <CircleAlert aria-hidden="true" />
            Launch blocked
          </span>
        )}
      </div>
      <div className="trip-row-actions">
        <Link
          className="setup-guide-action"
          href={operationsHref("/overview", trip)}
        >
          <span>Open Trip Overview</span>
          <ArrowRight aria-hidden="true" />
        </Link>
      </div>
    </article>
  );
}

function singleSearchParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

function normalizeStatusFilter(value: string | string[] | undefined): string {
  const raw = singleSearchParam(value);
  const allowed = new Set([
    "all",
    "published",
    "draft",
    "open_booking",
    "closed_booking",
    "sold_out",
  ]);

  return allowed.has(raw) ? raw : "all";
}

function tripMatchesFilters(
  trip: WorkspaceTrip,
  {
    query,
    statusFilter,
  }: {
    query: string;
    statusFilter: string;
  },
): boolean {
  const matchesQuery =
    !query || trip.title.toLowerCase().includes(query.toLowerCase());
  const matchesStatus =
    statusFilter === "all" ||
    (statusFilter === "published" && trip.publicationState === "published") ||
    (statusFilter === "draft" && trip.publicationState !== "published") ||
    (statusFilter === "open_booking" &&
      trip.effectiveBookingAvailability === "open") ||
    (statusFilter === "closed_booking" &&
      trip.effectiveBookingAvailability === "closed") ||
    (statusFilter === "sold_out" &&
      trip.effectiveBookingAvailability === "sold_out");

  return matchesQuery && matchesStatus;
}

function publicationStatusClass(value: string) {
  return value === "published" ? "is-clear" : "is-readonly";
}

function bookingStatusClass(value: string) {
  if (value === "open") {
    return "is-clear";
  }

  if (value === "sold_out") {
    return "is-blocked";
  }

  return "";
}

function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatShortDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}
