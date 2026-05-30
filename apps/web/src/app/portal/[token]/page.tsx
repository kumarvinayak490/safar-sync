import { redirect } from "next/navigation";

import {
  getTravelerPortal,
  startBalancePaymentCheckout,
  submitTravelerManualPayment,
  updateTravelerIdentity,
  type TravelerIdentity,
  type TravelerManualPayment
} from "@/lib/traveler-portal";

type TravelerPortalPageProps = {
  params: {
    token: string;
  };
  searchParams?: {
    attempt?: string;
    balance?: string;
    order?: string;
    payment?: string;
    saved?: string;
    error?: string;
  };
};

export default async function TravelerPortalPage({
  params,
  searchParams
}: TravelerPortalPageProps) {
  const portal = await getTravelerPortal(params.token);

  if (!portal.ok) {
    return (
      <main className="portal-shell">
        <section className="portal-empty" aria-label="Traveler Portal unavailable">
          <p className="eyebrow">Traveler Portal</p>
          <h1>Access link unavailable</h1>
          <p>Invalid or expired link.</p>
        </section>
      </main>
    );
  }

  async function saveTravelerIdentity(formData: FormData) {
    "use server";

    const travelerSlotId = Number(formData.get("traveler_slot_id"));
    const result = await updateTravelerIdentity({
      token: params.token,
      travelerSlotId,
      travelerFullName: String(formData.get("traveler_full_name") ?? ""),
      travelerPhone: String(formData.get("traveler_phone") ?? ""),
      travelerEmail: String(formData.get("traveler_email") ?? "")
    });

    const resultParam = result.ok
      ? `saved=${travelerSlotId}`
      : `error=${travelerSlotId}`;
    redirect(`/portal/${params.token}?${resultParam}`);
  }

  async function submitPaymentProof(formData: FormData) {
    "use server";

    const result = await submitTravelerManualPayment({
      token: params.token,
      amountInr: Number(formData.get("amount_inr")),
      paymentReference: String(formData.get("payment_reference") ?? ""),
      note: String(formData.get("note") ?? ""),
      paymentProof: formData.get("payment_proof") as File
    });

    redirect(`/portal/${params.token}?payment=${result.ok ? "submitted" : "error"}`);
  }

  async function startBalanceCheckout() {
    "use server";

    const result = await startBalancePaymentCheckout(params.token);
    if (!result.ok) {
      redirect(`/portal/${params.token}?balance=error`);
    }

    const query = new URLSearchParams({
      balance: "ready",
      attempt: String(result.paymentAttemptId),
      order: result.providerAttemptReference
    });
    redirect(`/portal/${params.token}?${query.toString()}`);
  }

  const scopeLabel =
    portal.accessScope === "booking" ? "Booking-Level Access" : "Traveler-Level Access";

  return (
    <main className="portal-shell">
      <section className="portal-header" aria-label="Traveler Portal">
        <div>
          <p className="eyebrow">{portal.organizerIdentity.name}</p>
          <h1>{portal.trip.title}</h1>
          <p>
            {formatDate(portal.trip.startDate)} to {formatDate(portal.trip.endDate)}
          </p>
        </div>
        <div className="portal-access-panel">
          <span>{scopeLabel}</span>
          <strong>{portal.booking.bookingStateLabel}</strong>
          <em>Expires {formatDateTime(portal.accessExpiresAt)}</em>
        </div>
      </section>

      <section className="portal-summary" aria-label="Booking summary">
        <SummaryItem label="Booking" value={`#${portal.booking.id}`} />
        <SummaryItem label="Reservation Amount" value={formatInr(portal.booking.bookingReservationAmountInr)} />
        <SummaryItem label="Booking Total" value={formatInr(portal.booking.bookingTotalInr)} />
        <SummaryItem label="Balance Due" value={formatInr(portal.balancePayment.amountInr)} />
        <SummaryItem label="Booking Contact" value={portal.bookingContact.name} />
      </section>

      <section className="portal-workspace" aria-label="Balance Payment Link">
        <div className="portal-section-heading">
          <h2>Balance Payment</h2>
          <p>Current balance due.</p>
        </div>

        <div className="portal-balance-panel">
          <div>
            <span>Amount due</span>
            <strong>{formatInr(portal.balancePayment.amountInr)}</strong>
            <em>{portal.balancePayment.message}</em>
          </div>
          <form action={startBalanceCheckout} className="portal-balance-action">
            {searchParams?.balance === "ready" ? (
              <p className="portal-form-note is-saved">
                Attempt #{searchParams.attempt} ready.
              </p>
            ) : null}
            {searchParams?.balance === "error" ? (
              <p className="portal-form-note is-error">Balance checkout not started</p>
            ) : null}
            <button disabled={!portal.balancePayment.available} type="submit">
              Start Balance Checkout
            </button>
          </form>
        </div>
      </section>

      <section className="portal-workspace" aria-label="Manual Payment proof">
        <div className="portal-section-heading">
          <h2>Manual Payment Proof</h2>
          <p>Upload proof for review.</p>
        </div>

        <div className="portal-payment-layout">
          <form action={submitPaymentProof} className="portal-payment-form">
            <label>
              <span>Amount paid</span>
              <input min="1" name="amount_inr" required type="number" />
            </label>
            <label>
              <span>Payment reference</span>
              <input name="payment_reference" placeholder="UPI or bank reference" />
            </label>
            <label>
              <span>Payment Proof</span>
              <input
                accept="image/*,.pdf"
                name="payment_proof"
                required
                type="file"
              />
            </label>
            <label>
              <span>Note</span>
              <textarea name="note" rows={3} />
            </label>
            <div className="portal-row-action">
              {searchParams?.payment === "submitted" ? (
                <p className="portal-form-note is-saved">Submitted for review</p>
              ) : null}
              {searchParams?.payment === "error" ? (
                <p className="portal-form-note is-error">Add amount and Payment Proof</p>
              ) : null}
              <button type="submit">Submit Payment Proof</button>
            </div>
          </form>

          <div className="portal-payment-list" aria-label="Submitted Manual Payments">
            {portal.manualPayments.length > 0 ? (
              portal.manualPayments.map((payment) => (
                <TravelerManualPaymentRow key={payment.id} payment={payment} />
              ))
            ) : (
              <div className="portal-payment-empty">
                <strong>No Manual Payments submitted</strong>
                <span>Proof status appears here.</span>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="portal-workspace" aria-label="Traveler Identity Details">
        <div className="portal-section-heading">
          <h2>Traveler Identity Details</h2>
          <p>Name, phone, optional email.</p>
        </div>

        <div className="portal-traveler-list">
          {portal.travelerSlots.map((traveler) => (
            <TravelerIdentityForm
              key={traveler.id}
              traveler={traveler}
              saved={searchParams?.saved === String(traveler.id)}
              errored={searchParams?.error === String(traveler.id)}
              action={saveTravelerIdentity}
            />
          ))}
        </div>
      </section>
    </main>
  );
}

function TravelerManualPaymentRow({ payment }: { payment: TravelerManualPayment }) {
  return (
    <div className="portal-payment-row">
      <div>
        <strong>{formatInr(payment.amountInr)}</strong>
        <span>{payment.paymentReference || "No reference"}</span>
        <em>{formatDateTime(payment.submittedAt)}</em>
      </div>
      <span className={`status-chip manual-payment-${payment.status}`}>
        {payment.statusLabel}
      </span>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value || "Not supplied"}</strong>
    </div>
  );
}

function TravelerIdentityForm({
  traveler,
  saved,
  errored,
  action
}: {
  traveler: TravelerIdentity;
  saved: boolean;
  errored: boolean;
  action: (formData: FormData) => void;
}) {
  return (
    <form action={action} className="portal-traveler-row">
      <input type="hidden" name="traveler_slot_id" value={traveler.id} />
      <div className="portal-traveler-state">
        <span>Traveler Slot {traveler.position}</span>
        <strong>{traveler.isTraveler ? traveler.travelerFullName : "Identity pending"}</strong>
        <em>{traveler.packageName}</em>
      </div>
      <label>
        <span>Full name</span>
        <input
          name="traveler_full_name"
          autoComplete="name"
          defaultValue={traveler.travelerFullName}
          required
        />
      </label>
      <label>
        <span>Phone</span>
        <input
          name="traveler_phone"
          autoComplete="tel"
          defaultValue={traveler.travelerPhone}
          required
        />
      </label>
      <label>
        <span>Email</span>
        <input
          name="traveler_email"
          autoComplete="email"
          defaultValue={traveler.travelerEmail}
          type="email"
        />
      </label>
      <div className="portal-row-action">
        {saved ? <p className="portal-form-note is-saved">Saved</p> : null}
        {errored ? <p className="portal-form-note is-error">Check name and phone</p> : null}
        <button type="submit">
          {traveler.isTraveler ? "Update Traveler" : "Save Traveler"}
        </button>
      </div>
    </form>
  );
}

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(amount);
}

function formatDate(value: string) {
  if (!value) {
    return "Date pending";
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(new Date(value));
}

function formatDateTime(value: string) {
  if (!value) {
    return "soon";
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
