import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTripOverviewReadModel,
  type TripOverview,
} from "./trip-overview.ts";

test("Trip Overview summary stays compact for a newly created Trip", () => {
  const overview = tripOverview({
    providerPaymentSetupComplete: false,
    bookings: 0,
    reservedTravelers: 0,
    missingRequirements: 0,
  });

  const model = buildTripOverviewReadModel(overview);

  assert.equal(model.dateRange, "10 Oct 2026 to 15 Oct 2026");
  assert.deepEqual(model.statusPills, [
    { label: "Draft Public Trip Page", tone: "readonly" },
    { label: "Closed Booking Availability", tone: "readonly" },
  ]);
  assert.equal(model.launchContext.href, "/operations/trips/7/launch");
  assert.equal(
    model.paymentRows.find((row) => row.label === "Payment methods")?.href,
    "/operations/trips/7/launch",
  );
  assert.equal(
    model.paymentRows.find((row) => row.label === "Payment methods")?.detail,
    "Razorpay online payments: Online Payment Readiness blocked; Manual Payments: Manual Payment Instructions missing",
  );
  assert.equal(model.packageRows[0]?.reservationAmount, "INR 8,000");
  assert.deepEqual(model.recentActivity, []);
});

test("Trip Overview summary routes operational attention to Trip workspace pages", () => {
  const overview = tripOverview({
    providerPaymentSetupComplete: true,
    bookings: 2,
    reservedTravelers: 3,
    missingRequirements: 4,
    pendingManualPayments: 1,
    dueInr: 24000,
    recentActivity: [
      {
        id: 9,
        action: "traveler_replaced",
        actionLabel: "Traveler Replaced",
        bookingId: 12,
        travelerSlotId: 44,
        actorEmail: "operator@example.com",
        occurredAt: "2026-05-25T10:30:00+05:30",
        metadata: {},
      },
    ],
  });

  const model = buildTripOverviewReadModel(overview);

  assert.equal(
    model.paymentRows.find((row) => row.label === "Due")?.value,
    "INR 24,000",
  );
  assert.equal(
    model.paymentRows.find((row) => row.label === "Payment methods")?.href,
    "/operations/trips/7/payments",
  );
  assert.equal(
    model.readinessRows.find((row) => row.label === "Requirements")?.href,
    "/operations/trips/7/travelers",
  );
  assert.equal(model.recentActivity[0]?.label, "Traveler Replaced");
  assert.equal(model.recentActivity[0]?.detail, "Booking #12");
});

test("Trip Overview payment summary names ready Manual Payments separately from Razorpay", () => {
  const overview = tripOverview({
    providerPaymentSetupComplete: false,
    manualPaymentReady: true,
    bookings: 0,
    reservedTravelers: 0,
    missingRequirements: 0,
  });

  const model = buildTripOverviewReadModel(overview);
  const paymentMethods = model.paymentRows.find(
    (row) => row.label === "Payment methods",
  );

  assert.equal(paymentMethods?.value, "Ready");
  assert.equal(paymentMethods?.href, "/operations/trips/7/payments");
  assert.equal(
    paymentMethods?.detail,
    "Manual Payments ready; Razorpay online payments: Online Payment Readiness blocked",
  );
});

function tripOverview({
  providerPaymentSetupComplete,
  manualPaymentReady = false,
  bookings,
  reservedTravelers,
  missingRequirements,
  pendingManualPayments = 0,
  dueInr = 0,
  recentActivity = [],
}: {
  providerPaymentSetupComplete: boolean;
  manualPaymentReady?: boolean;
  bookings: number;
  reservedTravelers: number;
  missingRequirements: number;
  pendingManualPayments?: number;
  dueInr?: number;
  recentActivity?: TripOverview["recentActivity"];
}): TripOverview {
  return {
    trip: {
      id: 7,
      title: "Spiti Winter Field Week",
      startDate: "2026-10-10",
      endDate: "2026-10-15",
      publicationState: "draft",
      publicationStateLabel: "Draft",
      bookingAvailability: "closed",
      bookingAvailabilityLabel: "Closed",
      publicUrlPath: "/trips/himalayan-monsoon-cohort/spiti-winter-field-week",
    },
    capacity: {
      totalSeats: 24,
      availableSeats: 24 - reservedTravelers,
      reservedTravelers,
      coreOperationalBookingCount: bookings,
    },
    packages: [
      {
        id: 3,
        name: "Standard shared room",
        description: "Shared room package.",
        priceInr: 32000,
        reservationAmountInr: 8000,
        position: 1,
      },
    ],
    bookingProgress: {
      coreOperationalBookingCount: bookings,
      bookingStateCounts: bookings
        ? {
            reserved: bookings,
          }
        : {},
      bookings: [],
    },
    paymentReadiness: {
      providerPaymentSetupComplete,
      providerPaymentSetupStatusLabel: providerPaymentSetupComplete
        ? "Complete"
        : "Not started",
      onlinePaymentReadinessReady: providerPaymentSetupComplete,
      onlinePaymentReadinessStatusLabel: providerPaymentSetupComplete
        ? "Ready"
        : "Blocked",
      onlinePaymentReadinessMessage: providerPaymentSetupComplete
        ? "Online Payment Readiness is ready for public booking."
        : "Provider verification must be verified before public booking can open.",
      paymentMethodReadinessReady:
        providerPaymentSetupComplete || manualPaymentReady,
      paymentMethodReadinessStatusLabel:
        providerPaymentSetupComplete || manualPaymentReady
          ? "Ready"
          : "Blocked",
      readyPaymentMethodCount:
        Number(providerPaymentSetupComplete) + Number(manualPaymentReady),
      readyPaymentMethodIds: [
        ...(providerPaymentSetupComplete ? ["provider_payments"] : []),
        ...(manualPaymentReady ? ["qr_manual_payments"] : []),
      ],
      paymentMethods: paymentMethods(
        providerPaymentSetupComplete,
        manualPaymentReady,
      ),
      providerPaymentMethod: paymentMethods(providerPaymentSetupComplete)[0],
      manualPaymentMethod: paymentMethods(
        providerPaymentSetupComplete,
        manualPaymentReady,
      )[1],
      collectedInr: 0,
      dueInr,
      overdueInr: 0,
      refundDueInr: 0,
      platformFeeInr: 0,
      grossProviderPaymentAmountInr: 0,
      providerFeeAmountInr: 0,
      providerNetSettlementAmountInr: 0,
      providerPaymentCount: 0,
      providerPaymentsWithFeeCount: 0,
      providerPaymentsWithNetSettlementCount: 0,
      pendingManualPayments,
    },
    travelerReadiness: {
      reservedTravelers,
      missingRequirements,
      missingRequirementsSupported: true,
      ready: missingRequirements === 0,
    },
    launchContext: {
      publicationState: "draft",
      publicationStateLabel: "Draft",
      bookingAvailability: "closed",
      bookingAvailabilityLabel: "Closed",
      effectiveBookingAvailability: "closed",
      effectiveBookingAvailabilityLabel: "Closed",
      message: "Public booking is closed.",
    },
    recentActivity,
  };
}

function paymentMethods(onlineReady: boolean, manualReady = false) {
  return [
    {
      id: "provider_payments",
      label: "Online payments",
      methodType: "provider_payment",
      ready: onlineReady,
      statusLabel: onlineReady ? "Ready" : "Blocked",
      blockerCode: onlineReady ? "ready" : "online_payment_readiness_blocked",
      blockerLabel: onlineReady ? "Ready" : "Online Payment Readiness blocked",
      message: onlineReady
        ? "Online payments are ready for public booking."
        : "Provider verification must be verified before public booking can open.",
      actionLabel: "Pay online",
      provider: "razorpay",
      providerLabel: "Razorpay",
      onlinePaymentReadinessReady: onlineReady,
      manualPaymentInstructionsReady: null,
      manualPaymentAvailabilityOpen: null,
      requiresReview: false,
    },
    {
      id: "qr_manual_payments",
      label: "Manual Payments",
      methodType: "qr_manual_payment",
      ready: manualReady,
      statusLabel: manualReady ? "Ready" : "Blocked",
      blockerCode: manualReady
        ? "ready"
        : "manual_payment_instructions_missing",
      blockerLabel: manualReady
        ? "Ready"
        : "Manual Payment Instructions missing",
      message: manualReady
        ? "Manual Payments are ready for this Trip."
        : "Manual Payments require Manual Payment Instructions before travelers can scan a Payment QR.",
      actionLabel: "Scan QR code to pay",
      provider: "",
      providerLabel: "",
      onlinePaymentReadinessReady: null,
      manualPaymentInstructionsReady: manualReady,
      manualPaymentAvailabilityOpen: manualReady,
      requiresReview: true,
    },
  ];
}
