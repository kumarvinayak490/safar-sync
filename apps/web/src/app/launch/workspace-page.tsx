import Link from "next/link";
import { redirect } from "next/navigation";

import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import { FormSubmitButton } from "@/components/ui/form-submit-button";
import type { TripWorkspaceRouteContext } from "@/app/workspace";
import { getOperationsDashboard } from "@/lib/operations-dashboard";
import {
  isPublicTripPagePublished,
  publicTripPagePublishDisabledReason,
} from "@/lib/workspace";

import {
  openPublicBookingAction,
  publishPublicTripPageAction,
  setManualPaymentAvailabilityAction,
} from "./actions";

export const metadata = {
  title: "Launch | TripOS",
  description: "Trip Launch Checklist for TripOS organizers",
};

export default async function LaunchPage({
  activePath,
  currentPath,
  workspace,
}: TripWorkspaceRouteContext) {
  const dashboard = await getOperationsDashboard();

  if (!dashboard.ok) {
    if (dashboard.status === "unauthenticated") {
      redirect("/login");
    }

    return (
      <main className="launch-shell">
        <section className="launch-workbench">
          <div className="onboarding-panel">
            <div className="section-heading">
              <h1>Launch is not available</h1>
              <p>Your User does not have access to this Organizer workspace.</p>
            </div>
          </div>
        </section>
      </main>
    );
  }

  const trip = workspace.selectedTrip;
  if (!trip) {
    const isOwner = dashboard.membership.role === "owner";

    return (
      <OperationsWorkspaceShell
        activePath={activePath}
        currentPath={currentPath}
        workspace={workspace}
      >
        <OperationalEmptyState
          eyebrow="Launch"
          title="No Trip is ready for Launch"
          body={
            isOwner
              ? "Create a draft Trip first. Launch will appear after the Trip exists."
              : "An Owner must create a Trip before Operators can review launch readiness."
          }
        />
      </OperationsWorkspaceShell>
    );
  }

  const isOwner = dashboard.membership.role === "owner";
  const readiness = trip.launchReadiness;
  const profileReadiness = trip.tripProfilePublicationReadiness;
  const canOpenBooking = dashboard.permissions.canOpenBookingAvailability;
  const publicTripPath = trip.publicUrlPath;
  const publicTripPagePublished = isPublicTripPagePublished(trip);
  const publishDisabledReason = publicTripPagePublishDisabledReason({
    roleLabel: dashboard.membership.label,
    trip,
  });
  const publishDisabled = Boolean(publishDisabledReason);
  const providerPaymentMethod = readiness.providerPaymentMethod;
  const manualPaymentMethod = readiness.manualPaymentMethod;
  const manualPaymentAvailabilityOpen =
    trip.manualPaymentAvailability === "open" ||
    manualPaymentMethod.manualPaymentAvailabilityOpen === true;
  const manualPaymentInstructionsReady =
    manualPaymentMethod.manualPaymentInstructionsReady === true;
  const manualPaymentMissingInstructions =
    manualPaymentMethod.blockerCode === "manual_payment_instructions_missing" ||
    !manualPaymentInstructionsReady;
  const canOpenWithManualPayments =
    manualPaymentAvailabilityOpen &&
    manualPaymentInstructionsReady &&
    readiness.capacityAvailable;
  const canOpenByEnablingManualPayments =
    !manualPaymentAvailabilityOpen &&
    manualPaymentInstructionsReady &&
    readiness.capacityAvailable;
  const openDisabled =
    !canOpenBooking ||
    readiness.bookingAvailabilityOpen ||
    !readiness.publicationReady ||
    (!readiness.paymentMethodReadinessReady &&
      !canOpenWithManualPayments &&
      !canOpenByEnablingManualPayments) ||
    !readiness.capacityAvailable;
  const manualPaymentActionDisabled =
    !isOwner ||
    (!manualPaymentAvailabilityOpen &&
      (!readiness.bookingAvailabilityOpen || !manualPaymentInstructionsReady));
  const providerPaymentEnabled = providerPaymentMethod.ready;
  const manualPaymentToggleOn = manualPaymentAvailabilityOpen;
  const manualPaymentStatusLabel = manualPaymentInstructionsReady
    ? manualPaymentAvailabilityOpen
      ? "Enabled"
      : canOpenByEnablingManualPayments
        ? "Ready to open"
        : "Off"
    : "Setup needed";
  const manualPaymentDetail = manualPaymentInstructionsReady
    ? manualPaymentAvailabilityOpen
      ? "Scan QR code to pay"
      : canOpenByEnablingManualPayments
        ? "Turn on to open Public Booking with Manual Payments"
        : readiness.bookingAvailabilityOpen
          ? "Available to enable"
          : "Open Public Booking first"
    : "Add Payment QR in Payment Setup";
  const paymentOptionsStatusLabel = readiness.paymentMethodReadinessReady
    ? readiness.paymentMethodReadinessStatusLabel
    : canOpenByEnablingManualPayments
      ? "Manual Payments ready"
      : readiness.paymentMethodReadinessStatusLabel;
  const openPublicBookingLabel =
    canOpenByEnablingManualPayments && !manualPaymentAvailabilityOpen
      ? "Open Public Booking with Manual Payments"
      : "Open Public Booking";
  const manualPaymentToggleTitle = manualPaymentActionDisabled
    ? !isOwner
      ? "Only Owners can manage Manual Payment Availability."
      : manualPaymentInstructionsReady
        ? "Open Public Booking before changing Manual Payments."
        : manualPaymentMethod.message
    : undefined;

  const checklist = [
    {
      label: "Trip Profile Publication Readiness",
      detail: profileReadiness.publishEligible
        ? "Required profile sections are clear."
        : `${profileReadiness.blockerCount} blockers before publishing.`,
      done: profileReadiness.publishEligible,
    },
    {
      label: "Public Trip Page",
      detail: readiness.publicationReady
        ? "Visible to travelers."
        : "Publish before payment setup is ready.",
      done: readiness.publicationReady,
    },
    {
      label: "Payment methods",
      detail: readiness.paymentMethodReadinessReady
        ? `${readiness.readyPaymentMethodCount} method ready for public booking.`
        : canOpenByEnablingManualPayments
          ? "Manual Payments are ready. Open Public Booking to activate them."
          : "Open at least one ready payment method.",
      done:
        readiness.paymentMethodReadinessReady || canOpenByEnablingManualPayments,
    },
    {
      label: "Capacity",
      detail: `${readiness.availableSeats} seats available from ${trip.capacity} capacity.`,
      done: readiness.capacityAvailable,
    },
    {
      label: "Public booking",
      detail: readiness.bookingAvailabilityOpen
        ? readiness.message
        : "Bookings opening soon.",
      done: readiness.ready,
    },
  ];

  return (
    <OperationsWorkspaceShell
      activePath={activePath}
      currentPath={currentPath}
      workspace={workspace}
    >
      <section aria-labelledby="launch-title">
        <header className="launch-header">
          <div>
            <p className="eyebrow">{workspace.organizer.name}</p>
            <h1 id="launch-title">Trip Launch Checklist</h1>
            <p>{trip.title}</p>
          </div>
          <div className="launch-status-panel" aria-label="Launch status">
            <span>{dashboard.membership.label}</span>
            <strong>
              {readiness.ready ? "Ready for booking" : readiness.message}
            </strong>
            <em>
              {formatShortDate(trip.startDate)} to{" "}
              {formatShortDate(trip.endDate)}
            </em>
          </div>
        </header>

        <section className="launch-summary" aria-label="Trip launch summary">
          <div>
            <span>Publication State</span>
            <strong>{titleCase(trip.publicationState)}</strong>
          </div>
          <div>
            <span>Booking Availability</span>
            <strong>{readiness.effectiveBookingAvailabilityLabel}</strong>
          </div>
          <div>
            <span>Available Seats</span>
            <strong>{readiness.availableSeats}</strong>
          </div>
        </section>

        <section className="launch-grid">
          <aside className="launch-actions" aria-label="Launch actions">
            <div className="launch-payment-options-card">
              <span>Payment options</span>
              <strong>{paymentOptionsStatusLabel}</strong>
              <div
                className="launch-payment-options"
                aria-label="Trip payment options"
              >
                <div
                  aria-checked={providerPaymentEnabled}
                  aria-disabled="true"
                  aria-label={`${providerPaymentMethod.providerLabel || "Razorpay"} online payments`}
                  className={`launch-payment-option ${
                    providerPaymentEnabled ? "is-on" : "is-unavailable"
                  }`}
                  role="switch"
                >
                  <div className="launch-payment-option-main">
                    <span aria-hidden="true" className="launch-payment-switch" />
                    <div>
                      <strong>
                        {providerPaymentMethod.providerLabel || "Razorpay"}
                      </strong>
                      <em>
                        {providerPaymentEnabled
                          ? "Pay online"
                          : "Complete Razorpay setup"}
                      </em>
                    </div>
                  </div>
                  <span
                    className={`status-chip ${
                      providerPaymentEnabled ? "is-clear" : "is-neutral"
                    }`}
                  >
                    {providerPaymentEnabled ? "Enabled" : "Setup needed"}
                  </span>
                </div>

                <form action={setManualPaymentAvailabilityAction}>
                  <input
                    name="organizerId"
                    type="hidden"
                    value={dashboard.activeOrganizer.id}
                  />
                  <input name="tripId" type="hidden" value={trip.id} />
                  <input
                    name="manualPaymentAvailability"
                    type="hidden"
                    value={manualPaymentAvailabilityOpen ? "closed" : "open"}
                  />
                  {canOpenByEnablingManualPayments &&
                  !readiness.bookingAvailabilityOpen ? (
                    <input name="openBookingTogether" type="hidden" value="on" />
                  ) : null}
                  <FormSubmitButton
                    aria-checked={manualPaymentToggleOn}
                    aria-label="Manual Payments"
                    className={`launch-payment-option-button ${
                      manualPaymentToggleOn ? "is-on" : ""
                    } ${manualPaymentInstructionsReady ? "" : "is-unavailable"}`}
                    disabled={manualPaymentActionDisabled}
                    pendingChildren="Updating Manual Payments..."
                    role="switch"
                    title={manualPaymentToggleTitle}
                  >
                    <span className="launch-payment-option-main">
                      <span
                        aria-hidden="true"
                        className="launch-payment-switch"
                      />
                      <span>
                        <strong>Manual Payments</strong>
                        <em>{manualPaymentDetail}</em>
                      </span>
                    </span>
                    <span
                      className={`status-chip ${
                        manualPaymentInstructionsReady
                          ? manualPaymentToggleOn
                            ? "is-clear"
                            : "is-neutral"
                          : "is-neutral"
                      }`}
                    >
                      {manualPaymentStatusLabel}
                    </span>
                  </FormSubmitButton>
                </form>
              </div>
              {manualPaymentMissingInstructions && isOwner ? (
                <Link className="settings-link" href="/payment-setup">
                  Add Manual Payment Instructions
                </Link>
              ) : null}
              {!isOwner ? (
                <p className="launch-permission-note">
                  Operators can view Manual Payment Availability.
                </p>
              ) : null}
            </div>

            <div>
              <span>Public booking</span>
              <strong>{readiness.effectiveBookingAvailabilityLabel}</strong>
              <p>{readiness.message}</p>
              {!readiness.paymentMethodReadinessReady &&
              manualPaymentMissingInstructions &&
              isOwner ? (
                <Link className="settings-link" href="/payment-setup">
                  Open Payment Setup
                </Link>
              ) : null}
              {!readiness.paymentMethodReadinessReady && !isOwner ? (
                <p className="launch-permission-note">Owner-managed blocker.</p>
              ) : null}
              <form action={openPublicBookingAction}>
                <input
                  name="organizerId"
                  type="hidden"
                  value={dashboard.activeOrganizer.id}
                />
                <input name="tripId" type="hidden" value={trip.id} />
                {canOpenByEnablingManualPayments ? (
                  <input name="openManualPayments" type="hidden" value="on" />
                ) : null}
                <FormSubmitButton
                  disabled={openDisabled}
                  pendingChildren="Opening Public Booking..."
                  title={openDisabled ? readiness.message : undefined}
                >
                  {openPublicBookingLabel}
                </FormSubmitButton>
              </form>
              {canOpenByEnablingManualPayments &&
              !readiness.bookingAvailabilityOpen ? (
                <p className="launch-permission-note">
                  Manual Payments are configured. Use the button above or turn on
                  Manual Payments to open booking.
                </p>
              ) : null}
            </div>

            <div>
              <span>Public page</span>
              <strong>{publicTripPagePublished ? "Published" : "Draft"}</strong>
              <p>
                {publicTripPagePublished
                  ? "Published page is ready for travelers."
                  : "Publish when profile blockers are clear."}
              </p>
              {publicTripPagePublished && publicTripPath ? (
                <div
                  className="public-page-link"
                  aria-label="Public Trip Page link"
                >
                  <span>Share link</span>
                  <code>{publicTripPath}</code>
                  <Link className="settings-link" href={publicTripPath}>
                    Open Public Trip Page
                  </Link>
                </div>
              ) : null}
              {!publicTripPagePublished ? (
                <div
                  className="launch-profile-readiness"
                  aria-label="Trip Profile Publication Readiness checklist"
                >
                  <div>
                    <strong>Trip Profile Publication Readiness</strong>
                    <span>
                      {profileReadiness.publishEligible
                        ? "Ready"
                        : `${profileReadiness.blockerCount} blockers`}
                    </span>
                  </div>
                  {profileReadiness.blockers.length ? (
                    profileReadiness.blockers.map((item) => (
                      <p key={item.id}>{item.label}</p>
                    ))
                  ) : (
                    <p>Required profile items are complete.</p>
                  )}
                  {profileReadiness.encouraged.length ? (
                    <em>
                      Encouraged:{" "}
                      {profileReadiness.encouraged
                        .map((item) => item.label)
                        .join(", ")}
                    </em>
                  ) : null}
                </div>
              ) : null}
              {!publicTripPagePublished ? (
                <form action={publishPublicTripPageAction}>
                  <input
                    name="organizerId"
                    type="hidden"
                    value={dashboard.activeOrganizer.id}
                  />
                  <input name="tripId" type="hidden" value={trip.id} />
                  <input name="currentPath" type="hidden" value={currentPath} />
                  <input
                    name="publishLockAcknowledged"
                    type="hidden"
                    value="on"
                  />
                  <FormSubmitButton
                    disabled={publishDisabled}
                    pendingChildren="Publishing Public Trip Page..."
                    title={publishDisabledReason}
                  >
                    Publish Public Trip Page
                  </FormSubmitButton>
                </form>
              ) : null}
            </div>

            {!isOwner ? (
              <p className="launch-permission-note">Owner action required.</p>
            ) : null}
          </aside>

          <div className="launch-checklist" aria-label="Launch checklist">
            <header className="launch-checklist-heading">
              <span>Readiness</span>
              <strong>Launch checklist</strong>
            </header>
            {checklist.map((item) => (
              <div className={item.done ? "is-done" : ""} key={item.label}>
                <span>{item.done ? "Ready" : "Needed"}</span>
                <strong>{item.label}</strong>
                <em>{item.detail}</em>
              </div>
            ))}
          </div>
        </section>
      </section>
    </OperationsWorkspaceShell>
  );
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
