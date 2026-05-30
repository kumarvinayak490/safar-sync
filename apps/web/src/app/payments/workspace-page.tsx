import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import { ManualPaymentApprovalQueue } from "@/app/payments/ManualPaymentApprovalQueue";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import {
  buildPaymentsOperationModel,
  type PaymentsOperationModel,
} from "@/lib/trip-operations";
import { getTripOverview } from "@/lib/trip-overview";

export const metadata = {
  title: "Payments | TripOS",
  description: "TripOS payment workspace",
};

export default async function PaymentsPage({
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
          eyebrow="Payments"
          title="Payments are unavailable"
          body="The selected Trip payment summary could not be loaded. Open Trips and choose another Trip, or retry when the API is reachable."
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
        <PaymentsWorkbench
          model={buildPaymentsOperationModel(overview)}
          organizerId={workspace.organizer.id}
        />
      ) : (
        <OperationalEmptyState
          eyebrow="Payments"
          title="No Trip selected"
          body={
            isOwner
              ? "Create or open a Trip before using Trip-level Payments."
              : "An Owner must create a Trip before Operators can use Trip-level Payments."
          }
        />
      )}
    </OperationsWorkspaceShell>
  );
}

function PaymentsWorkbench({
  model,
  organizerId,
}: {
  model: PaymentsOperationModel;
  organizerId: number;
}) {
  return (
    <section className="trip-operation-page" aria-labelledby="payments-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Trip-level Payments</p>
          <h2 id="payments-title">{model.context.tripTitle}</h2>
          <p className="workspace-heading-copy">{model.context.dateRange}</p>
        </div>
      </div>

      <div
        className="operation-summary-grid payment-summary-grid"
        aria-label="Payment summary"
      >
        {model.metrics.map((metric) => (
          <div className={`metric-tile is-${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <em>{metric.detail}</em>
          </div>
        ))}
      </div>

      <section
        className="operation-panel"
        aria-label="Booking payment balances"
      >
        <div className="section-heading">
          <p className="eyebrow">Financial Ledger</p>
          <h3>Booking payment balances</h3>
        </div>
        {model.balanceRows.length ? (
          <div className="operation-table payments-table" role="table">
            <div
              className="operation-row payment-balance-row header"
              role="row"
            >
              <span role="columnheader">Booking Contact</span>
              <span role="columnheader">Payment State</span>
              <span role="columnheader">Booking Total</span>
              <span role="columnheader">Collected</span>
              <span role="columnheader">Due</span>
              <span role="columnheader">Refund</span>
            </div>
            {model.balanceRows.map((row) => (
              <div
                className="operation-row payment-balance-row"
                id={`payment-booking-${row.id}`}
                key={row.id}
                role="row"
              >
                <span className="queue-identity-cell" role="cell">
                  <strong>{row.bookingContactName}</strong>
                  <em>{row.balanceLabel}</em>
                </span>
                <span
                  className={`status-chip is-${row.paymentTone}`}
                  role="cell"
                >
                  {row.paymentStateLabel}
                </span>
                <strong className="queue-money" role="cell">
                  {row.bookingTotal}
                </strong>
                <strong className="queue-money" role="cell">
                  {row.collectedAmount}
                </strong>
                <span
                  className={`queue-balance-cell is-${row.balanceTone}`}
                  role="cell"
                >
                  <strong>{row.dueAmount}</strong>
                  <em>{row.balanceLabel}</em>
                </span>
                <strong className="queue-money" role="cell">
                  {row.refundDueAmount}
                </strong>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <span>No payment records yet</span>
            <strong>
              Trip-level Payments open after Bookings reserve seats
            </strong>
            <p>Booking balances appear here.</p>
          </div>
        )}
      </section>

      <section
        className="operation-panel"
        aria-label="Provider payment reconciliation"
      >
        <div className="section-heading">
          <p className="eyebrow">Provider Reconciliation</p>
          <h3>Provider payment details</h3>
        </div>
        {model.providerPaymentRows.length ? (
          <div
            className="operation-table provider-reconciliation-table"
            role="table"
          >
            <div
              className="operation-row provider-reconciliation-row header"
              role="row"
            >
              <span role="columnheader">Booking Contact</span>
              <span role="columnheader">Purpose</span>
              <span role="columnheader">Gross Collected</span>
              <span role="columnheader">Provider Fee</span>
              <span role="columnheader">Net Settlement</span>
              <span role="columnheader">TripOS Platform Fee</span>
              <span role="columnheader">Provider Reference</span>
              <span role="columnheader">Confirmed</span>
            </div>
            {model.providerPaymentRows.map((row) => (
              <div
                className="operation-row provider-reconciliation-row"
                key={row.id}
                role="row"
              >
                <span className="queue-identity-cell" role="cell">
                  <strong>{row.bookingContactName}</strong>
                  <em>{row.providerLabel}</em>
                </span>
                <span className="status-chip is-readonly" role="cell">
                  {row.purposeLabel}
                </span>
                <span className="queue-money-stack" role="cell">
                  <strong>{row.grossAmount}</strong>
                  <em>Booking balance</em>
                </span>
                <span className="queue-money-stack" role="cell">
                  <strong>{row.providerFeeAmount}</strong>
                  <em>{row.providerFeeDetail}</em>
                </span>
                <span className="queue-money-stack" role="cell">
                  <strong>{row.providerNetSettlementAmount}</strong>
                  <em>{row.providerNetSettlementDetail}</em>
                </span>
                <span className="queue-money-stack" role="cell">
                  <strong>{row.platformFeeAmount}</strong>
                  <em>{row.platformFeeDetail}</em>
                </span>
                <span className="queue-reference-cell" role="cell">
                  {row.providerReferenceLabel}
                </span>
                <span role="cell">{row.confirmedAtLabel}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <span>No Provider Payments recorded</span>
            <strong>Provider reconciliation is clear</strong>
            <p>Provider deductions appear after confirmation.</p>
          </div>
        )}
      </section>

      <section
        className="operation-panel"
        aria-label="Manual Payment approval queue"
      >
        <div className="section-heading">
          <p className="eyebrow">Manual Payments</p>
          <h3>Approval queue</h3>
        </div>
        {model.manualPaymentRows.length ? (
          <ManualPaymentApprovalQueue
            organizerId={organizerId}
            rows={model.manualPaymentRows}
            tripId={model.context.tripId}
          />
        ) : (
          <div className="empty-state">
            <span>No Manual Payments submitted</span>
            <strong>Approval queue is clear</strong>
            <p>
              Submitted Payment Proof and Payment Acknowledgement review appear
              here.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}
