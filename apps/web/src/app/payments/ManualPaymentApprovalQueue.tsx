"use client";

import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ExternalLink, X } from "lucide-react";

import {
  approveManualPaymentAction,
  rejectManualPaymentAction,
} from "@/app/payments/actions";
import { FormSubmitButton } from "@/components/ui/form-submit-button";
import type { ManualPaymentApprovalRow } from "@/lib/trip-operations";

export function ManualPaymentApprovalQueue({
  organizerId,
  rows,
  tripId,
}: {
  organizerId: number;
  rows: ManualPaymentApprovalRow[];
  tripId: number;
}) {
  const [selectedPaymentId, setSelectedPaymentId] = useState<number | null>(
    null,
  );
  const [modalRoot, setModalRoot] = useState<HTMLElement | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const titleId = useId();
  const selectedPayment =
    rows.find((row) => row.id === selectedPaymentId) ?? null;

  useEffect(() => {
    setModalRoot(document.body);
  }, []);

  useEffect(() => {
    if (!selectedPayment) {
      return;
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedPaymentId(null);
      }
    }

    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [selectedPayment]);

  

  useEffect(() => {
    if (!selectedPayment) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [selectedPayment]);

  const reviewModal = selectedPayment ? (
    <div
      className="manual-payment-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          setSelectedPaymentId(null);
        }
      }}
    >
      <section
        aria-labelledby={titleId}
        aria-modal="true"
        className="manual-payment-modal"
        role="dialog"
      >
        <div className="manual-payment-modal-header">
          <div>
            <p className="eyebrow">Manual Payment review</p>
            <h3 id={titleId}>{selectedPayment.bookingContactName}</h3>
          </div>
          <button
            aria-label="Close Manual Payment review"
            className="manual-payment-modal-close"
            onClick={() => setSelectedPaymentId(null)}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="manual-payment-modal-body">
          <figure className="manual-payment-proof-frame">
            {selectedPayment.proofDownloadHref ? (
              <img
                alt={`Payment Proof submitted by ${selectedPayment.bookingContactName}`}
                src={selectedPayment.proofDownloadHref}
              />
            ) : (
              <figcaption>No Payment Proof attached</figcaption>
            )}
          </figure>

          <div className="manual-payment-review-summary">
            <dl>
              <div>
                <dt>Amount</dt>
                <dd>{selectedPayment.amount}</dd>
              </div>
              <div>
                <dt>Reference Number</dt>
                <dd>{selectedPayment.referenceLabel}</dd>
              </div>
              <div>
                <dt>Travelers</dt>
                <dd>{selectedPayment.travelerCountLabel}</dd>
              </div>
              <div>
                <dt>Package</dt>
                <dd>{selectedPayment.packageContext}</dd>
              </div>
              <div>
                <dt>Submitted</dt>
                <dd>{selectedPayment.submittedAtLabel}</dd>
              </div>
              <div>
                <dt>Payment Proof</dt>
                <dd>
                  {selectedPayment.proofLabel}
                  {selectedPayment.proofDownloadHref ? (
                    <a href={selectedPayment.proofDownloadHref}>
                      <ExternalLink aria-hidden="true" size={14} />
                      <span>Open file</span>
                    </a>
                  ) : null}
                </dd>
              </div>
            </dl>

            <div className="manual-payment-modal-actions">
              <form action={approveManualPaymentAction}>
                <input name="organizerId" type="hidden" value={organizerId} />
                <input name="tripId" type="hidden" value={tripId} />
                <input
                  name="manualPaymentId"
                  type="hidden"
                  value={selectedPayment.id}
                />
                <FormSubmitButton
                  className="manual-payment-review-button is-approve"
                  pendingChildren="Approving"
                >
                  <Check aria-hidden="true" size={15} />
                  <span>Approve</span>
                </FormSubmitButton>
              </form>
              <form action={rejectManualPaymentAction}>
                <input name="organizerId" type="hidden" value={organizerId} />
                <input name="tripId" type="hidden" value={tripId} />
                <input
                  name="manualPaymentId"
                  type="hidden"
                  value={selectedPayment.id}
                />
                <FormSubmitButton
                  className="manual-payment-review-button is-reject"
                  pendingChildren="Denying"
                >
                  <X aria-hidden="true" size={15} />
                  <span>Deny</span>
                </FormSubmitButton>
              </form>
            </div>
          </div>
        </div>
      </section>
    </div>
  ) : null;

  return (
    <>
      <div className="operation-table manual-payments-table" role="table">
        <div className="operation-row manual-payment-row header" role="row">
          <span role="columnheader">Booking Contact</span>
          <span role="columnheader">Travelers</span>
          <span role="columnheader">Package</span>
          <span role="columnheader">Amount</span>
          <span role="columnheader">Reference</span>
          <span role="columnheader">Payment Proof</span>
          <span role="columnheader">Review</span>
          <span role="columnheader">Submitted</span>
        </div>
        {rows.map((row) => (
          <div
            aria-haspopup="dialog"
            aria-label={`Review Manual Payment from ${row.bookingContactName}`}
            className="operation-row manual-payment-row manual-payment-review-trigger"
            key={row.id}
            onClick={() => setSelectedPaymentId(row.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setSelectedPaymentId(row.id);
              }
            }}
            role="row"
            tabIndex={0}
          >
            <span className="queue-identity-cell" role="cell">
              <strong>{row.bookingContactName}</strong>
              <em>{row.sourceLabel}</em>
            </span>
            <span role="cell">{row.travelerCountLabel}</span>
            <span role="cell">{row.packageContext}</span>
            <strong className="queue-money" role="cell">
              {row.amount}
            </strong>
            <span className="queue-reference-cell" role="cell">
              {row.referenceLabel}
            </span>
            <span className="queue-money-stack" role="cell">
              <strong>{row.proofLabel}</strong>
              <em>{row.proofSensitivityLabel}</em>
            </span>
            <span className="manual-payment-review-cell" role="cell">
              <span className={`status-chip is-${row.statusTone}`}>
                {row.statusLabel}
              </span>
              <span className="queue-row-action">Review proof</span>
            </span>
            <span role="cell">{row.submittedAtLabel}</span>
          </div>
        ))}
      </div>

      {modalRoot && reviewModal ? createPortal(reviewModal, modalRoot) : null}
    </>
  );
}
