import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildTravelersOperationModel,
  type TravelersOperationModel,
} from "@/lib/trip-operations";
import { getTripOverview } from "@/lib/trip-overview";

export const metadata = {
  title: "Travelers | TripOS",
  description: "TripOS traveler workspace",
};

export default async function TravelersPage({
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
          eyebrow="Travelers"
          title="Travelers are unavailable"
          body="The selected Trip traveler readiness summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
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
        <TravelersWorkbench model={buildTravelersOperationModel(overview)} />
      ) : (
        <OperationalEmptyState
          eyebrow="Travelers"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Travelers."
              : "An Owner must create a Trip before Operators can use Travelers."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function TravelersWorkbench({ model }: { model: TravelersOperationModel }) {
  return (
    <section className="trip-operation-page" aria-labelledby="travelers-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Travelers</p>
          <h2 id="travelers-title">{model.context.tripTitle}</h2>
          <p className="workspace-heading-copy">
            {model.context.dateRange}
          </p>
        </div>
      </div>

      <div className="operation-summary-grid" aria-label="Traveler readiness summary">
        {model.metrics.map((metric) => (
          <div className={`metric-tile is-${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.detail}</em>
          </div>
        ))}
      </div>
      <div>
        <section className="operation-panel" aria-label="Traveler readiness rows">
          <div className="section-heading">
            <p className="eyebrow">Selected Trip</p>
            <h3>Traveler readiness queue</h3>
          </div>
          {model.requirementRows.length ? (
            <div className="operation-table travelers-table" role="table">
              <div
                className="operation-row traveler-readiness-row header"
                role="row"
              >
                <span role="columnheader">Booking Contact</span>
                <span role="columnheader">Booking State</span>
                <span role="columnheader">Travelers</span>
                <span role="columnheader">Payment</span>
                <span role="columnheader">Readiness</span>
              </div>
              {model.requirementRows.map((row) => (
                <a
                  className="operation-row traveler-readiness-row"
                  href={row.travelerHref}
                  id={`traveler-booking-${row.id}`}
                  key={row.id}
                  role="row"
                >
                  <span className="queue-identity-cell" role="cell">
                    <strong>{row.bookingContactName}</strong>
                    <em>{row.requirementDetail}</em>
                  </span>
                  <span className="queue-chip-stack" role="cell">
                    <span className={`status-chip state-${row.bookingState}`}>
                      {row.bookingStateLabel}
                    </span>
                  </span>
                  <span role="cell">{row.travelerSlotCount}</span>
                  <span className={`status-chip is-${row.paymentTone}`} role="cell">
                    {row.paymentStateLabel}
                  </span>
                  <span className={`status-chip is-${row.readinessTone}`} role="cell">
                    {row.readinessLabel}
                  </span>
                </a>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <span>No reserved Travelers yet</span>
              <strong>Readiness opens after Bookings reserve seats</strong>
              <p>Traveler requirements appear here.</p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
