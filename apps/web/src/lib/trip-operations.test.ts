import assert from "node:assert/strict";
import test from "node:test";

import {
  TRIP_OPERATION_AREAS,
  buildBookingsOperationModel,
  buildCommunicationsOperationModel,
  buildExportsOperationModel,
  buildPaymentsOperationModel,
  buildTravelersOperationModel,
  tripOperationHref,
} from "./trip-operations.ts";
import type { TripOverview } from "./trip-overview.ts";

test("Trip operation areas are selected Trip workspace routes", () => {
  assert.deepEqual(Object.keys(TRIP_OPERATION_AREAS), [
    "bookings",
    "payments",
    "travelers",
    "communications",
    "exports",
  ]);
  assert.equal(
    tripOperationHref("bookings", 7),
    "/operations/trips/7/bookings",
  );
  assert.equal(
    tripOperationHref("payments", 7),
    "/operations/trips/7/payments",
  );
  assert.equal(
    tripOperationHref("travelers", 7),
    "/operations/trips/7/travelers",
  );
  assert.equal(
    tripOperationHref("communications", 7),
    "/operations/trips/7/communications",
  );
  assert.equal(tripOperationHref("exports", 7), "/operations/trips/7/exports");
});

test("Bookings model scopes rows to the selected Trip overview", () => {
  const model = buildBookingsOperationModel(tripOverview());

  assert.equal(model.context.tripId, 7);
  assert.equal(model.context.selectedTripHref, "/operations/trips/7/bookings");
  assert.deepEqual(
    model.rows.map((row) => ({
      id: row.id,
      href: row.bookingHref,
      contact: row.bookingContactName,
      balance: row.balanceLabel,
      collected: row.collectedAmount,
      readiness: row.readinessLabel,
    })),
    [
      {
        id: 41,
        href: "/operations/trips/7/travelers#traveler-booking-41",
        contact: "Asha Nair",
        balance: "INR 30,000 due",
        collected: "INR 15,000",
        readiness: "2 missing",
      },
      {
        id: 42,
        href: "/operations/trips/7/travelers#traveler-booking-42",
        contact: "Rahul Menon",
        balance: "Balance clear",
        collected: "INR 15,000",
        readiness: "Ready",
      },
    ],
  );
  assert.equal(model.metrics[0].detail, "1 reserved, 1 confirmed");
});

test("Payments model separates Trip-level reconciliation from Payment Setup", () => {
  const model = buildPaymentsOperationModel(tripOverview());

  assert.equal(model.context.selectedTripHref, "/operations/trips/7/payments");
  assert.match(model.scopeNote, /Organizer-level Payment Setup/);
  assert.deepEqual(
    model.balanceRows.map((row) => ({
      contact: row.bookingContactName,
      state: row.paymentStateLabel,
      due: row.dueAmount,
      balance: row.balanceLabel,
    })),
    [
      {
        contact: "Asha Nair",
        state: "Reservation paid",
        due: "INR 30,000",
        balance: "INR 30,000 due",
      },
      {
        contact: "Rahul Menon",
        state: "Fully paid",
        due: "INR 0",
        balance: "Balance clear",
      },
    ],
  );
  assert.deepEqual(
    model.manualPaymentRows.map((row) => ({
      contact: row.bookingContactName,
      travelers: row.travelerCountLabel,
      packageContext: row.packageContext,
      status: row.statusLabel,
      amount: row.amount,
      proof: row.proofLabel,
      sensitivity: row.proofSensitivityLabel,
      download: row.proofDownloadHref,
    })),
    [
      {
        contact: "Asha Nair",
        travelers: "3 Travelers",
        packageContext: "Standard shared room x 3",
        status: "Submitted",
        amount: "INR 10,000",
        proof: "asha-upi.png",
        sensitivity: "Sensitive Payment Information",
        download:
          "http://localhost:8000/api/operations/organizers/2/manual-payments/81/proof-download/",
      },
    ],
  );
  assert.deepEqual(
    model.providerPaymentRows.map((row) => ({
      contact: row.bookingContactName,
      gross: row.grossAmount,
      providerFee: row.providerFeeAmount,
      netSettlement: row.providerNetSettlementAmount,
      platformFee: row.platformFeeAmount,
    })),
    [
      {
        contact: "Asha Nair",
        gross: "INR 15,000",
        providerFee: "INR 420",
        netSettlement: "INR 14,580",
        platformFee: "INR 300",
      },
      {
        contact: "Rahul Menon",
        gross: "INR 15,000",
        providerFee: "Not reported",
        netSettlement: "Not reported",
        platformFee: "INR 300",
      },
    ],
  );
  assert.equal(
    model.metrics.find((metric) => metric.label === "Manual Payment approvals")
      ?.value,
    "1",
  );
  assert.equal(
    model.metrics.find((metric) => metric.label === "Provider fees")?.value,
    "INR 420",
  );
  assert.equal(
    model.metrics.find((metric) => metric.label === "TripOS Platform Fee")
      ?.value,
    "INR 600",
  );
});

test("Travelers model keeps readiness summaries inside Travelers", () => {
  const model = buildTravelersOperationModel(tripOverview());

  assert.equal(model.context.selectedTripHref, "/operations/trips/7/travelers");
  assert.equal(model.metrics[1].label, "Missing Confirmation Requirements");
  assert.equal(
    model.metrics[2].detail,
    "No separate Requirements tab in this workspace",
  );
  assert.deepEqual(
    model.requirementCategories
      .filter((category) => category.sensitive)
      .map((category) => category.label),
    ["Traveler Documents", "Medical Disclosure"],
  );
  assert.ok(
    model.requirementCategories.some(
      (category) => category.label === "Emergency Contact",
    ),
  );
  assert.deepEqual(
    model.requirementRows.map((row) => ({
      href: row.travelerHref,
      state: row.bookingStateLabel,
      payment: row.paymentStateLabel,
      readiness: row.readinessLabel,
    })),
    [
      {
        href: "/operations/trips/7/travelers#traveler-booking-41",
        state: "Reserved",
        payment: "Reservation paid",
        readiness: "2 missing",
      },
      {
        href: "/operations/trips/7/travelers#traveler-booking-42",
        state: "Confirmed",
        payment: "Fully paid",
        readiness: "Ready",
      },
    ],
  );
});

test("Communications model is limited to Trip Reminders and Announcements", () => {
  const model = buildCommunicationsOperationModel(tripOverview());

  assert.equal(
    model.context.selectedTripHref,
    "/operations/trips/7/communications",
  );
  assert.deepEqual(
    model.queues.map((queue) => queue.type),
    ["Reminder", "Reminder", "Announcement"],
  );
  assert.deepEqual(
    model.queues.map((queue) => queue.channelLabel),
    ["WhatsApp and email", "WhatsApp and email", "WhatsApp and email"],
  );
  assert.match(model.queues[2].audienceDetail, /without mirroring WhatsApp/);
  assert.equal(model.metrics[2].label, "Organizer templates");
  assert.equal(model.metrics[2].value, "None");
});

test("Exports model builds Trip-scoped CSV handoffs without a Vendors module", () => {
  const model = buildExportsOperationModel({
    organizerId: 3,
    overview: tripOverview(),
  });

  assert.equal(model.context.selectedTripHref, "/operations/trips/7/exports");
  assert.equal(model.metrics[2].value, "Trip CSV");
  assert.equal(model.metrics[2].detail, "Trip-scoped field-team handoff");
  assert.equal(
    model.options[0].href,
    "http://localhost:8000/api/operations/organizers/3/trips/7/operational-export.csv",
  );
  assert.equal(
    model.options[1].href,
    "http://localhost:8000/api/operations/organizers/3/trips/7/operational-export.csv?include_sensitive_traveler_information=true&include_sensitive_payment_information=true",
  );
  assert.deepEqual(
    model.options.map((option) => ({
      action: option.actionLabel,
      policy: option.policyLabel,
      sensitivity: option.sensitivityLabel,
      tone: option.sensitivityTone,
    })),
    [
      {
        action: "Download CSV",
        policy: "Default Operational Export",
        sensitivity: "Sensitive fields excluded",
        tone: "clear",
      },
      {
        action: "Download explicit CSV",
        policy: "Explicit sensitive selection",
        sensitivity: "Sensitive fields included",
        tone: "blocked",
      },
    ],
  );
});

function tripOverview(): TripOverview {
  return {
    trip: {
      id: 7,
      title: "Spiti Field Week",
      startDate: "2026-10-10",
      endDate: "2026-10-15",
      publicationState: "published",
      publicationStateLabel: "Published",
      bookingAvailability: "open",
      bookingAvailabilityLabel: "Open",
      publicUrlPath: "/trips/himalayan-monsoon/spiti-field-week",
    },
    capacity: {
      totalSeats: 24,
      availableSeats: 20,
      reservedTravelers: 4,
      coreOperationalBookingCount: 2,
    },
    packages: [],
    bookingProgress: {
      coreOperationalBookingCount: 2,
      bookingStateCounts: { reserved: 1, confirmed: 1 },
      bookings: [
        {
          id: 41,
          bookingState: "reserved",
          bookingStateLabel: "Reserved",
          bookingContactName: "Asha Nair",
          travelerSlotCount: 3,
          bookingTotalInr: 45000,
          bookingReservationAmountInr: 15000,
          paymentState: "reservation_paid",
          paymentStateLabel: "Reservation paid",
          reconciliation: {
            collectedInr: 15000,
            dueInr: 30000,
            overdueInr: 0,
            refundDueInr: 0,
            platformFeeInr: 300,
          },
          confirmationRequirements: {
            ready: false,
            unmetCount: 2,
          },
          providerPayments: [
            {
              id: 91,
              provider: "razorpay",
              providerLabel: "Razorpay",
              paymentPurpose: "reservation",
              paymentPurposeLabel: "Reservation",
              providerAttemptReference: "order_asha_001",
              providerPaymentReference: "pay_asha_001",
              grossAmountInr: 15000,
              providerFeeAmountInr: 420,
              providerNetSettlementAmountInr: 14580,
              platformFeeInr: 300,
              confirmedAt: "2026-09-01T09:45:00+05:30",
            },
          ],
          manualPayments: [
            {
              id: 81,
              source: "traveler_submitted",
              sourceLabel: "Traveler-submitted",
              status: "submitted",
              statusLabel: "Submitted",
              amountInr: 10000,
              paymentReference: "UPI-asha-1",
              originalFilename: "asha-upi.png",
              hasPaymentProof: true,
              paymentProofStatusLabel:
                "Payment Proof attached, Sensitive Payment Information",
              paymentProofDownloadUrl:
                "/api/operations/organizers/2/manual-payments/81/proof-download/",
              isSensitivePaymentInformation: true,
              excludeFromDefaultExports: true,
              bookingContactName: "Asha Nair",
              travelerCount: 3,
              packageContext: "Standard shared room x 3",
              submittedAt: "2026-09-01T10:00:00+05:30",
            },
          ],
        },
        {
          id: 42,
          bookingState: "confirmed",
          bookingStateLabel: "Confirmed",
          bookingContactName: "Rahul Menon",
          travelerSlotCount: 1,
          bookingTotalInr: 15000,
          bookingReservationAmountInr: 15000,
          paymentState: "fully_paid",
          paymentStateLabel: "Fully paid",
          reconciliation: {
            collectedInr: 15000,
            dueInr: 0,
            overdueInr: 0,
            refundDueInr: 0,
            platformFeeInr: 300,
          },
          confirmationRequirements: {
            ready: true,
            unmetCount: 0,
          },
          providerPayments: [
            {
              id: 92,
              provider: "razorpay",
              providerLabel: "Razorpay",
              paymentPurpose: "reservation",
              paymentPurposeLabel: "Reservation",
              providerAttemptReference: "order_rahul_001",
              providerPaymentReference: "pay_rahul_001",
              grossAmountInr: 15000,
              providerFeeAmountInr: null,
              providerNetSettlementAmountInr: null,
              platformFeeInr: 300,
              confirmedAt: "2026-09-01T10:15:00+05:30",
            },
          ],
          manualPayments: [],
        },
      ],
    },
    paymentReadiness: {
      providerPaymentSetupComplete: true,
      providerPaymentSetupStatusLabel: "Complete",
      onlinePaymentReadinessReady: true,
      onlinePaymentReadinessStatusLabel: "Ready",
      onlinePaymentReadinessMessage:
        "Online Payment Readiness is ready for public booking.",
      paymentMethodReadinessReady: true,
      paymentMethodReadinessStatusLabel: "Ready",
      readyPaymentMethodCount: 1,
      readyPaymentMethodIds: ["provider_payments"],
      paymentMethods: paymentMethodsFixture(true),
      providerPaymentMethod: paymentMethodsFixture(true)[0],
      manualPaymentMethod: paymentMethodsFixture(true)[1],
      collectedInr: 30000,
      dueInr: 30000,
      overdueInr: 0,
      refundDueInr: 0,
      platformFeeInr: 600,
      grossProviderPaymentAmountInr: 30000,
      providerFeeAmountInr: 420,
      providerNetSettlementAmountInr: 14580,
      providerPaymentCount: 2,
      providerPaymentsWithFeeCount: 1,
      providerPaymentsWithNetSettlementCount: 1,
      pendingManualPayments: 1,
    },
    travelerReadiness: {
      reservedTravelers: 4,
      missingRequirements: 2,
      missingRequirementsSupported: true,
      ready: false,
    },
    launchContext: {
      publicationState: "published",
      publicationStateLabel: "Published",
      bookingAvailability: "open",
      bookingAvailabilityLabel: "Open",
      effectiveBookingAvailability: "open",
      effectiveBookingAvailabilityLabel: "Open",
      message: "Booking can start for this trip.",
    },
    recentActivity: [],
  };
}

function paymentMethodsFixture(onlineReady: boolean) {
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
      ready: false,
      statusLabel: "Blocked",
      blockerCode: "manual_payment_instructions_missing",
      blockerLabel: "Manual Payment Instructions missing",
      message:
        "Manual Payments require Manual Payment Instructions before travelers can scan a Payment QR.",
      actionLabel: "Scan QR code to pay",
      provider: "",
      providerLabel: "",
      onlinePaymentReadinessReady: null,
      manualPaymentInstructionsReady: false,
      manualPaymentAvailabilityOpen: false,
      requiresReview: true,
    },
  ];
}
