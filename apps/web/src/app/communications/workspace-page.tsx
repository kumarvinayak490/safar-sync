import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildCommunicationsOperationModel,
  type CommunicationsOperationModel,
} from "@/lib/trip-operations";
import { getTripOverview } from "@/lib/trip-overview";

export const metadata = {
  title: "Communications | TripOS",
  description: "TripOS Trip-scoped communications",
};

export default async function CommunicationsPage({
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
          eyebrow="Communications"
          title="Communications are unavailable"
          body="The selected Trip communications summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
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
        <CommunicationsWorkbench
          model={buildCommunicationsOperationModel(overview)}
        />
      ) : (
        <OperationalEmptyState
          eyebrow="Communications"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Communications."
              : "An Owner must create a Trip before Operators can use Communications."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function CommunicationsWorkbench({
  model,
}: {
  model: CommunicationsOperationModel;
}) {
  return (
    <section className="trip-operation-page" aria-labelledby="communications-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Communications</p>
          <h2 id="communications-title">{model.context.tripTitle}</h2>
          <p className="workspace-heading-copy">
            {model.context.dateRange}
          </p>
        </div>
      </div>

      <div className="operation-summary-grid" aria-label="Communications summary">
        {model.metrics.map((metric) => (
          <div className={`metric-tile is-${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.detail}</em>
          </div>
        ))}
      </div>

      <section className="operation-panel" aria-label="Reminder and Announcement queues">
        <div className="section-heading">
          <p className="eyebrow">Selected Trip</p>
          <h3>Reminders</h3>
        </div>
        <div className="operation-table communications-table" role="table">
          <div
            className="operation-row communication-queue-row header"
            role="row"
          >
            <span role="columnheader">Notification</span>
            <span role="columnheader">Type</span>
            <span role="columnheader">Audience</span>
            <span role="columnheader">Channel</span>
            <span role="columnheader">Status</span>
          </div>
          {model.queues.map((queue) => (
            <div
              className="operation-row communication-queue-row"
              key={queue.id}
              role="row"
            >
              <span className="queue-identity-cell" role="cell">
                <strong>{queue.title}</strong>
                <em>{queue.audienceDetail}</em>
              </span>
              <span className="status-chip is-readonly" role="cell">
                {queue.type}
              </span>
              <span role="cell">{queue.audience}</span>
              <span role="cell">{queue.channelLabel}</span>
              <span className={`status-chip is-${queue.tone}`} role="cell">
                {queue.status}
              </span>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
