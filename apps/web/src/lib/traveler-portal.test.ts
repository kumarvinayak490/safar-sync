import assert from "node:assert/strict";
import test from "node:test";

import { getTravelerPortal, startBalancePaymentCheckout } from "./traveler-portal.ts";

test("traveler portal adapter exposes booking-scoped balance payment availability", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () =>
    Response.json({
      access_scope: "booking",
      access_expires_at: "2026-06-09T12:00:00Z",
      organizer_identity: {
        name: "Spiti Field Collective",
        logo_url: "",
        fallback: {
          initials: "SF",
          background: "oklch(0.92 0.04 150)",
          foreground: "oklch(0.32 0.07 150)"
        },
        placeholder: false
      },
      trip: {
        id: 7,
        title: "Spiti Winter Field Week",
        start_date: "2026-10-10",
        end_date: "2026-10-15"
      },
      booking: {
        id: 29,
        booking_state: "reserved",
        booking_state_label: "Reserved",
        booking_total_inr: 32000,
        booking_reservation_amount_inr: 8000
      },
      balance_payment: {
        available: true,
        blocker_code: "ready",
        message: "Balance Payment Link is ready.",
        amount_inr: 24000,
        currency: "INR",
        payment_purpose: "balance",
        payment_link_path: "/portal/link-token/"
      },
      booking_contact: {
        name: "Asha Nair",
        phone: "+919876543210",
        email: "asha@example.com"
      },
      manual_payments: [],
      traveler_slots: []
    });

  try {
    const portal = await getTravelerPortal("link-token");

    assert.equal(portal.ok, true);
    if (portal.ok) {
      assert.equal(portal.balancePayment.available, true);
      assert.equal(portal.balancePayment.amountInr, 24000);
      assert.equal(portal.balancePayment.paymentPurpose, "balance");
      assert.equal(portal.balancePayment.paymentLinkPath, "/portal/link-token/");
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("balance checkout client starts provider checkout through the portal token", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedMethod = "";

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedMethod = init?.method ?? "GET";
    return Response.json(
      {
        id: 31,
        booking: 29,
        provider: "razorpay",
        purpose: "balance",
        status: "pending",
        amount_inr: 24000,
        provider_attempt_reference: "order_balance_checkout_001",
        checkout: {
          provider: "razorpay",
          provider_order_reference: "order_balance_checkout_001",
          amount_inr: 24000,
          amount_minor: 2400000,
          currency: "INR",
          payment_attempt: 31,
          booking: 29,
          payment_purpose: "balance",
          provider_payload: {
            order_id: "order_balance_checkout_001",
            amount: 2400000,
            currency: "INR"
          }
        }
      },
      { status: 201 }
    );
  };

  try {
    const result = await startBalancePaymentCheckout("link-token");

    assert.equal(
      requestedUrl,
      "http://localhost:8000/api/portal/link-token/balance-payment-attempts/"
    );
    assert.equal(requestedMethod, "POST");
    assert.deepEqual(result, {
      ok: true,
      bookingId: 29,
      paymentAttemptId: 31,
      provider: "razorpay",
      purpose: "balance",
      status: "pending",
      amountInr: 24000,
      providerAttemptReference: "order_balance_checkout_001",
      checkout: {
        provider: "razorpay",
        providerOrderReference: "order_balance_checkout_001",
        amountInr: 24000,
        amountMinor: 2400000,
        currency: "INR",
        paymentAttempt: 31,
        booking: 29,
        paymentPurpose: "balance",
        providerPayload: {
          order_id: "order_balance_checkout_001",
          amount: 2400000,
          currency: "INR"
        }
      }
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
