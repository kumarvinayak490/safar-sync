import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildExportsOperationModel,
  type ExportsOperationModel,
} from "@/lib/trip-operations";
import { getTripOverview } from "@/lib/trip-overview";

export const metadata = {
  title: "Exports | TripOS",
  description: "TripOS operational exports",
};

export default async function ExportsPage({
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
          eyebrow="Exports"
          title="Exports are unavailable"
          body="The selected Trip export summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
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
        <ExportsWorkbench
          model={buildExportsOperationModel({
            organizerId: workspace.organizer.id,
            overview,
          })}
        />
      ) : (
        <OperationalEmptyState
          eyebrow="Exports"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Exports."
              : "An Owner must create a Trip before Operators can use Exports."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function ExportsWorkbench({ model }: { model: ExportsOperationModel }) {
  return (
    <section className="trip-operation-page" aria-labelledby="exports-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Exports</p>
          <h2 id="exports-title">{model.context.tripTitle}</h2>
          <p className="workspace-heading-copy">
            {model.context.dateRange}
          </p>
        </div>
      </div>

      <div className="operation-summary-grid" aria-label="Operational Export summary">
        {model.metrics.map((metric) => (
          <div className={`metric-tile is-${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.detail}</em>
          </div>
        ))}
      </div>

      <section className="operation-panel" aria-label="Operational Export options">
        <div className="section-heading">
          <p className="eyebrow">Selected Trip</p>
          <h3>CSV handoffs</h3>
        </div>
        <div className="operation-table exports-table" role="table">
          <div className="operation-row export-option-row header" role="row">
            <span role="columnheader">Operational Export</span>
            <span role="columnheader">Policy</span>
            <span role="columnheader">Sensitive Data</span>
            <span role="columnheader">Action</span>
          </div>
          {model.options.map((option) => (
            <div
              className="operation-row export-option-row"
              key={option.id}
              role="row"
            >
              <span className="queue-identity-cell" role="cell">
                <strong>{option.title}</strong>
                <em>{option.description}</em>
              </span>
              <span role="cell">{option.policyLabel}</span>
              <span
                className={`status-chip is-${option.sensitivityTone}`}
                role="cell"
              >
                {option.sensitivityLabel}
              </span>
              <span role="cell">
                <a className="queue-row-action" href={option.href}>
                  {option.actionLabel}
                </a>
              </span>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
