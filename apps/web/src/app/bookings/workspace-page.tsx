import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildBookingsOperationModel,
  type BookingsOperationModel,
} from "@/lib/trip-operations";
import { getTripOverview } from "@/lib/trip-overview";

export const metadata = {
  title: "Bookings | TripOS",
  description: "TripOS Booking workspace",
};

export default async function BookingsPage({
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
          eyebrow="Bookings"
          title="Bookings are unavailable"
          body="The selected Trip Booking summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
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
        <BookingsWorkbench model={buildBookingsOperationModel(overview)} />
      ) : (
        <OperationalEmptyState
          eyebrow="Bookings"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Bookings."
              : "An Owner must create a Trip before Operators can use Bookings."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function BookingsWorkbench({ model }: { model: BookingsOperationModel }) {
  return (
    <section className="trip-operation-page" aria-labelledby="bookings-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Bookings</p>
          <h2 id="bookings-title">{model.context.tripTitle}</h2>
          <p className="workspace-heading-copy">
            {model.context.dateRange}
          </p>
        </div>
      </div>

      <div className="operation-summary-grid" aria-label="Booking summary">
        {model.metrics.map((metric) => (
          <div className={`metric-tile is-${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.detail}</em>
          </div>
        ))}
      </div>

      <section className="operation-panel" aria-label="Trip Booking rows">
        <div className="section-heading">
          <p className="eyebrow">Selected Trip</p>
          <h3>Booking queue</h3>
        </div>
        {model.rows.length ? (
          <div className="operation-table bookings-table" role="table">
            <div
              className="operation-row operation-row-booking header"
              role="row"
            >
              <span role="columnheader">Booking Contact</span>
              <span role="columnheader">Booking State</span>
              <span role="columnheader">Travelers</span>
              <span role="columnheader">Money</span>
              <span role="columnheader">Balance</span>
              <span role="columnheader">Readiness</span>
              <span role="columnheader">Action</span>
            </div>
            {model.rows.map((booking) => (
              <a
                className="operation-row operation-row-booking"
                href={booking.bookingHref}
                id={`booking-${booking.id}`}
                key={booking.id}
                role="row"
              >
                <span className="queue-identity-cell" role="cell">
                  <strong>{booking.bookingContactName}</strong>
                  <em>{booking.paymentStateLabel}</em>
                </span>
                <span className="queue-chip-stack" role="cell">
                  <span className={`status-chip is-${booking.paymentTone}`}>
                    {booking.paymentStateLabel}
                  </span>
                  <span className={`status-chip state-${booking.bookingState}`}>
                    {booking.bookingStateLabel}
                  </span>
                </span>
                <span role="cell">{booking.travelerSlotCount}</span>
                <span className="queue-money-stack" role="cell">
                  <strong>{booking.bookingTotal}</strong>
                  <em>{booking.collectedAmount} collected</em>
                  <em>{booking.reservationAmount} Reservation Amount</em>
                </span>
                <span
                  className={`queue-balance-cell is-${booking.balanceTone}`}
                  role="cell"
                >
                  <strong>{booking.balanceLabel}</strong>
                </span>
                <span
                  className={`status-chip is-${booking.readinessTone}`}
                  role="cell"
                >
                  {booking.readinessLabel}
                </span>
                <span className="queue-row-action" role="cell">
                  Review
                </span>
              </a>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <span>No Bookings yet</span>
            <strong>
              Trip operations will appear after seats are reserved
            </strong>
            <p>
              Booking rows appear here.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}
