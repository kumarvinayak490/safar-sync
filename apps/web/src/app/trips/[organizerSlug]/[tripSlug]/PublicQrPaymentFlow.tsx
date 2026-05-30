"use client";

import { useId, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  submitPublicManualPaymentProof,
  type PublicManualPaymentInstructions,
  type PublicTrip,
} from "@/lib/public-trip";

type PublicQrPaymentFlowProps = {
  organizerSlug: string;
  tripSlug: string;
  instructions: PublicManualPaymentInstructions;
  packages: PublicTrip["packages"];
};

type SubmissionState =
  | { status: "idle"; message: string }
  | { status: "submitting"; message: string }
  | {
      status: "success";
      message: string;
      bookingId: number;
      manualPaymentId: number;
    }
  | { status: "error"; message: string };

export function PublicQrPaymentFlow({
  organizerSlug,
  tripSlug,
  instructions,
  packages,
}: PublicQrPaymentFlowProps) {
  const qrInstructionId = useId();
  const [bookingContactName, setBookingContactName] = useState("");
  const [bookingContactPhone, setBookingContactPhone] = useState("");
  const [bookingContactEmail, setBookingContactEmail] = useState("");
  const [travelerCount, setTravelerCount] = useState(1);
  const [packageId, setPackageId] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [paymentProof, setPaymentProof] = useState<File | null>(null);
  const [qrVisible, setQrVisible] = useState(false);
  const [submission, setSubmission] = useState<SubmissionState>({
    status: "idle",
    message: "",
  });

  const selectedPackage = useMemo(
    () => packages.find((tripPackage) => String(tripPackage.id) === packageId),
    [packageId, packages],
  );
  const expectedAmount =
    (selectedPackage?.reservationAmountInr ?? 0) * Math.max(travelerCount, 1);
  const bookingDetailsComplete = Boolean(
    bookingContactName.trim() &&
      bookingContactPhone.trim() &&
      travelerCount > 0 &&
      selectedPackage,
  );
  const canSubmit =
    qrVisible &&
    bookingDetailsComplete &&
    paymentProof &&
    submission.status !== "submitting";

  async function submitPaymentProof(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!bookingDetailsComplete || !selectedPackage) {
      setQrVisible(false);
      setSubmission({
        status: "error",
        message:
          "Add Booking Contact Details, Traveler count, and Package before scanning the Payment QR.",
      });
      return;
    }
    if (!paymentProof) {
      setSubmission({
        status: "error",
        message: "Add Payment Proof before submitting.",
      });
      return;
    }

    setSubmission({
      status: "submitting",
      message: "Submitting Payment Proof for Organizer review.",
    });
    const result = await submitPublicManualPaymentProof({
      organizerSlug,
      tripSlug,
      bookingContactName,
      bookingContactPhone,
      bookingContactEmail,
      travelerCount,
      packageId: selectedPackage.id,
      paymentReference,
      paymentProof,
    });

    if (!result.ok) {
      setSubmission({ status: "error", message: result.message });
      return;
    }

    setSubmission({
      status: "success",
      message:
        "Payment Proof submitted. Seats reserve only after Organizer approval.",
      bookingId: result.bookingId,
      manualPaymentId: result.manualPaymentId,
    });
  }

  return (
    <form className="booking-intake-form" onSubmit={submitPaymentProof}>
      <fieldset disabled={submission.status === "success"}>
        <legend>Booking Contact Details</legend>
        <label>
          <span>Name</span>
          <input
            autoComplete="name"
            maxLength={160}
            onChange={(event) => {
              setBookingContactName(event.target.value);
              setQrVisible(false);
            }}
            required
            value={bookingContactName}
          />
        </label>
        <label>
          <span>Phone number</span>
          <input
            autoComplete="tel"
            maxLength={40}
            onChange={(event) => {
              setBookingContactPhone(event.target.value);
              setQrVisible(false);
            }}
            required
            value={bookingContactPhone}
          />
        </label>
        <label>
          <span>Email (optional)</span>
          <input
            autoComplete="email"
            onChange={(event) => {
              setBookingContactEmail(event.target.value);
              setQrVisible(false);
            }}
            type="email"
            value={bookingContactEmail}
          />
        </label>
      </fieldset>

      <fieldset disabled={submission.status === "success"}>
        <legend>Reservation Inputs</legend>
        <label>
          <span>Traveler count</span>
          <input
            inputMode="numeric"
            min={1}
            onChange={(event) => {
              setTravelerCount(Number(event.target.value));
              setQrVisible(false);
            }}
            required
            type="number"
            value={travelerCount}
          />
        </label>
        <label>
          <span>Package</span>
          <select
            onChange={(event) => {
              setPackageId(event.target.value);
              setQrVisible(false);
            }}
            required
            value={packageId}
          >
            <option value="">Select Package</option>
            {packages.map((tripPackage) => (
              <option
                value={tripPackage.id}
                key={tripPackage.id || tripPackage.name}
              >
                {tripPackage.name} ·{" "}
                {formatInr(tripPackage.reservationAmountInr)} Reservation Amount
              </option>
            ))}
          </select>
        </label>
      </fieldset>

      {!qrVisible ? (
        <div className="booking-intake-action">
          <p>
            {selectedPackage
              ? `${formatInr(expectedAmount)} Booking Reservation Amount.`
              : "Select a Package to calculate the Booking Reservation Amount."}
          </p>
          <button
            className="public-cta"
            disabled={!bookingDetailsComplete}
            onClick={() => {
              setQrVisible(true);
              setSubmission({ status: "idle", message: "" });
            }}
            type="button"
          >
            Continue to Payment QR
          </button>
        </div>
      ) : null}

      {qrVisible ? (
        <div
          aria-labelledby={qrInstructionId}
          className="public-manual-payment-panel"
          role="region"
        >
          <div className="public-manual-payment-copy">
            <strong id={qrInstructionId}>Scan QR code to pay</strong>
            <span>
              Pay {formatInr(expectedAmount)}. Payment Proof is reviewed by the
              Organizer before seats are reserved.
            </span>
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <figure className="public-payment-qr-frame">
            <img
              alt="Payment QR for Manual Payments"
              src={instructions.paymentQrUrl}
            />
            <figcaption>Payment QR</figcaption>
          </figure>
          <dl className="public-payment-instruction-list">
            {instructions.upiId ? (
              <div>
                <dt>UPI ID</dt>
                <dd>{instructions.upiId}</dd>
              </div>
            ) : null}
            {instructions.accountName ? (
              <div>
                <dt>Account name</dt>
                <dd>{instructions.accountName}</dd>
              </div>
            ) : null}
            {instructions.bankTransferDetails ? (
              <div>
                <dt>Bank transfer details</dt>
                <dd>{instructions.bankTransferDetails}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      ) : null}

      {qrVisible ? (
        <fieldset disabled={submission.status === "success"}>
          <legend>Payment Proof</legend>
          <label>
            <span>Payment reference (optional)</span>
            <input
              maxLength={160}
              onChange={(event) => setPaymentReference(event.target.value)}
              placeholder="UPI reference or bank transfer reference"
              value={paymentReference}
            />
          </label>
          <label>
            <span>Payment Proof</span>
            <input
              aria-describedby="payment-proof-help"
              accept="image/png,image/jpeg,image/webp,application/pdf"
              onChange={(event) =>
                setPaymentProof(event.target.files?.[0] ?? null)
              }
              required
              type="file"
            />
            <em id="payment-proof-help">
              PNG, JPG, WebP, or PDF proof of payment.
            </em>
          </label>
        </fieldset>
      ) : null}

      {submission.message ? (
        <div
          aria-live="polite"
          className={`draft-booking-notice ${
            submission.status === "success"
              ? "is-success"
              : submission.status === "error"
                ? "is-error"
                : "is-confirming"
          }`}
          role={submission.status === "error" ? "alert" : "status"}
        >
          <strong>
            {submission.status === "success"
              ? "Payment Proof received"
              : submission.status === "error"
                ? "Payment Proof not submitted"
                : "Submitting Payment Proof"}
          </strong>
          <span>
            {submission.message}
            {submission.status === "success"
              ? ` Booking #${submission.bookingId}, Manual Payment #${submission.manualPaymentId}.`
              : ""}
          </span>
        </div>
      ) : null}

      {qrVisible && submission.status !== "success" ? (
        <div className="booking-intake-action">
          <p>Submitted Manual Payments do not reserve seats until approved.</p>
          <button
            aria-busy={submission.status === "submitting"}
            className="public-cta"
            disabled={!canSubmit}
            type="submit"
          >
            {submission.status === "submitting"
              ? "Submitting Payment Proof..."
              : "Submit Payment Proof"}
          </button>
        </div>
      ) : null}
    </form>
  );
}

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    currency: "INR",
    maximumFractionDigits: 0,
    style: "currency",
  }).format(amount);
}
