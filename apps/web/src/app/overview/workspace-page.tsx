import type { CSSProperties } from "react";

import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildTripOverviewReadModel,
  getTripOverview,
  type TripOverviewTone,
} from "@/lib/trip-overview";

export const metadata = {
  title: "Trip Overview | TripOS",
  description: "TripOS selected Trip overview",
};

export default async function OverviewPage({
  activePath,
  currentPath,
  workspace,
}: TripWorkspaceRouteContext) {
  const isOwner = workspace.organizer.membership_role === "owner";
  const overview = workspace.selectedTrip
    ? await getTripOverview({
        organizerId: workspace.organizer.id,
        tripId: workspace.selectedTrip.id,
      })
    : null;

  if (overview && !overview.ok) {
    return (
      <OperationsWorkspaceShell
        activePath={activePath}
        currentPath={currentPath}
        workspace={workspace}
      >
        <OperationalEmptyState
          eyebrow="Overview"
          title="Trip Overview is unavailable"
          body="The selected Trip summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
        />
      </OperationsWorkspaceShell>
    );
  }

  return (
    <OperationsWorkspaceShell
      activePath={activePath}
      currentPath={currentPath}
      workspace={workspace}
    >
      {overview?.ok ? (
        <TripOverviewWorkbench overview={overview} />
      ) : (
        <OperationalEmptyState
          eyebrow="Overview"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Trip Overview."
              : "An Owner must create a Trip before Operators can use Trip Overview."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function TripOverviewWorkbench({
  overview,
}: {
  overview: Awaited<ReturnType<typeof getTripOverview>> & { ok: true };
}) {
  const model = buildTripOverviewReadModel(overview);
  const bookingFunnel = buildBookingFunnel(overview);
  const paymentTotal =
    overview.paymentReadiness.collectedInr +
    overview.paymentReadiness.dueInr +
    overview.paymentReadiness.refundDueInr;
  const collectedShare = paymentTotal
    ? Math.round((overview.paymentReadiness.collectedInr / paymentTotal) * 100)
    : 0;
  const dueShare = paymentTotal
    ? Math.round(
        ((overview.paymentReadiness.collectedInr +
          overview.paymentReadiness.dueInr) /
          paymentTotal) *
          100,
      )
    : 0;

  return (
    <section className="trip-overview">
      <section className="overview-context-band" aria-label="Trip operating context">
        <div className="overview-context-title">
          <p className="eyebrow">Trip Overview</p>
          <h2>Operations snapshot</h2>
          <span>
            {overview.capacity.reservedTravelers} of {overview.capacity.totalSeats} seats
            reserved, {overview.capacity.availableSeats} available,{" "}
            {model.packageRows.length || "no"} package
            {model.packageRows.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="overview-context-pills" aria-label="Launch status">
          {model.statusPills.map((pill) => (
            <span
              className={`status-chip ${statusChipClass(pill.tone)}`}
              key={pill.label}
            >
              {pill.label}
            </span>
          ))}
        </div>
      </section>

      <div className="overview-workspace-grid">
        <div className="overview-primary-flow">
          <section className="overview-panel" aria-label="Booking funnel">
            <div className="overview-panel-heading">
              <p className="eyebrow">Bookings</p>
              <h3>Booking Funnel</h3>
            </div>
            <div className="booking-funnel">
              {bookingFunnel.map((item) => (
                <div key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <em>
                    <i style={{ width: `${item.width}%` }} />
                  </em>
                </div>
              ))}
            </div>
          </section>

          <section
            className="overview-panel payment-overview-panel"
            aria-label="Payment readiness"
          >
            <div className="overview-panel-heading">
              <p className="eyebrow">Payments</p>
              <h3>Payments</h3>
            </div>
            <div className="payment-donut-row">
              <div
                aria-label={`${collectedShare}% collected`}
                className={`payment-donut ${paymentTotal ? "" : "is-empty"}`}
                style={
                  {
                    "--collected-share": `${collectedShare}%`,
                    "--due-share": `${dueShare}%`,
                  } as CSSProperties
                }
              >
                <strong>{formatInr(overview.paymentReadiness.collectedInr)}</strong>
                <span>Collected</span>
              </div>
              <div className="payment-readiness-list">
                {model.paymentRows.map((row) => (
                  <a className={`is-${row.tone}`} href={row.href} key={row.label}>
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
                    <em>{row.detail}</em>
                  </a>
                ))}
              </div>
            </div>
          </section>

          <section
            className={`overview-panel overview-launch-context is-${model.launchContext.tone}`}
            aria-label="Launch context"
          >
            <div className="overview-panel-heading">
              <p className="eyebrow">Launch</p>
              <h3>Launch context</h3>
            </div>
            <p>{model.launchContext.message}</p>
            <a className="overview-panel-link" href={model.launchContext.href}>
              Open Launch
            </a>
          </section>

          {model.packageRows.length ? (
            <section className="overview-package-strip" aria-label="Packages">
              <div className="overview-panel-heading">
                <p className="eyebrow">Packages</p>
                <h3>Packages</h3>
              </div>
              <div className="package-overview-list">
                {model.packageRows.map((tripPackage) => (
                  <article className="package-overview-row" key={tripPackage.id}>
                    <div>
                      <strong>{tripPackage.name}</strong>
                      {tripPackage.description ? <p>{tripPackage.description}</p> : null}
                    </div>
                    <dl>
                      <div>
                        <dt>Price</dt>
                        <dd>{tripPackage.price}</dd>
                      </div>
                      <div>
                        <dt>Reservation Amount</dt>
                        <dd>{tripPackage.reservationAmount}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="overview-right-rail" aria-label="Trip overview side panels">
          <section className="overview-panel" aria-label="Readiness summary">
            <div className="overview-panel-heading">
              <p className="eyebrow">Travelers</p>
              <h3>Traveler readiness</h3>
            </div>
            <div className="readiness-summary-list">
              {model.readinessRows.map((row) => (
                <a
                  className={`is-${row.tone}`}
                  href={row.href}
                  key={row.label}
                >
                  <span>
                    {row.label}
                    <em>{row.detail}</em>
                  </span>
                  <strong>{row.value}</strong>
                </a>
              ))}
            </div>
          </section>

          <section
            className="overview-panel overview-activity-panel"
            aria-label="Recent activity"
          >
            <div className="overview-panel-heading">
              <p className="eyebrow">Recent Activity</p>
              <h3>Operational changes</h3>
            </div>
            {model.recentActivity.length ? (
              <ol className="overview-activity-list">
                {model.recentActivity.map((activity) => (
                  <li key={activity.id}>
                    <span>{activity.occurredAt}</span>
                    <strong>{activity.label}</strong>
                    <em>{activity.detail}</em>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="empty-state standalone">
                <span>No activity yet</span>
                <strong>Trip operations have not started</strong>
                <p>Activity appears here.</p>
              </div>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

function buildBookingFunnel(
  overview: Awaited<ReturnType<typeof getTripOverview>> & { ok: true },
) {
  const counts = overview.bookingProgress.bookingStateCounts;
  const rows = [
    { label: "Draft", value: counts.draft ?? 0 },
    { label: "Reserved", value: counts.reserved ?? 0 },
    { label: "Confirmed", value: counts.confirmed ?? 0 },
    { label: "Cancelled", value: counts.cancelled ?? 0 },
  ];
  const max = Math.max(...rows.map((row) => row.value), 1);

  return rows.map((row) => ({
    ...row,
    width: Math.max(Math.round((row.value / max) * 100), row.value ? 18 : 8),
  }));
}

function statusChipClass(tone: TripOverviewTone): string {
  return tone === "attention" ? "is-attention" : `is-${tone}`;
}

function formatInr(value: number): string {
  return `INR ${new Intl.NumberFormat("en-IN").format(value)}`;
}
