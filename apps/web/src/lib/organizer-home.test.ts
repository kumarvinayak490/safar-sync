import assert from "node:assert/strict";
import test from "node:test";

import { buildOrganizerHomeReadModel } from "./organizer-home.ts";
import type { OperationsDashboard } from "./operations-dashboard.ts";
import type { WorkspaceTrip } from "./workspace.ts";

test("Organizer Home gives zero-Trip Owners an actionable setup guide", () => {
  const model = buildOrganizerHomeReadModel(
    dashboardFixture({ role: "owner", tripsCount: 0 }),
    [],
  );

  assert.equal(model.isOwner, true);
  assert.equal(model.hasTrips, false);
  assert.equal(model.primaryAction.action?.href, "/trips/new");
  assert.equal(model.zeroTripState.action?.label, "Create Trip");
  assert.equal(model.attentionItems[0]?.action, null);
  assert.deepEqual(
    model.setupGuide.map((item) => [item.id, item.action?.href ?? null]),
    [
      ["organizer_identity", "/organizer-identity"],
      ["team_access", "/team-access"],
      ["payment_setup", "/payment-setup"],
      ["create_trip", "/trips/new"],
    ],
  );
  assert.equal(
    model.setupGuide.find((item) => item.id === "create_trip")?.statusLabel,
    "Primary next action",
  );
});

test("Organizer Home keeps zero-Trip Operators read-only and explanatory", () => {
  const model = buildOrganizerHomeReadModel(
    dashboardFixture({ role: "operator", tripsCount: 0 }),
    [],
  );

  assert.equal(model.isOwner, false);
  assert.equal(model.hasTrips, false);
  assert.equal(model.primaryAction.action, null);
  assert.match(model.primaryAction.body, /must create a Trip/);
  assert.match(model.zeroTripState.body, /An Owner must create a Trip/);
  assert.equal(
    model.setupGuide.every((item) => item.action === null),
    true,
  );
  assert.equal(
    model.setupGuide.find((item) => item.id === "create_trip")?.readOnlyLabel,
    "Owner action required",
  );
  assert.match(
    model.setupGuide.find((item) => item.id === "payment_setup")?.body ?? "",
    /Razorpay online payments/,
  );
  assert.match(
    model.setupGuide.find((item) => item.id === "payment_setup")?.body ?? "",
    /Manual Payments/,
  );
});

test("Organizer Home presents Payment Setup as Organizer-level setup", () => {
  const model = buildOrganizerHomeReadModel(
    dashboardFixture({
      role: "owner",
      tripsCount: 1,
      providerPaymentSetupComplete: false,
      latestTrip: latestTripFixture({ launchReady: false }),
    }),
    [workspaceTripFixture()],
  );

  const paymentSetup = model.setupGuide.find(
    (item) => item.id === "payment_setup",
  );
  const paymentTile = model.summaryTiles.find(
    (item) => item.id === "payment_method_readiness",
  );

  assert.equal(paymentSetup?.action?.href, "/payment-setup");
  assert.match(paymentSetup?.body ?? "", /Razorpay online payments/);
  assert.match(paymentSetup?.body ?? "", /Manual Payments/);
  assert.equal(paymentTile?.label, "Payment methods");
  assert.match(paymentTile?.detail ?? "", /Razorpay online payments/);
  assert.match(paymentTile?.detail ?? "", /Manual Payments/);
});

test("Organizer Home summarizes Manual Payment readiness beside Razorpay", () => {
  const dashboard = dashboardFixture({
    role: "owner",
    tripsCount: 1,
    providerPaymentSetupComplete: false,
    latestTrip: latestTripFixture({ launchReady: true }),
  });
  const methods = paymentMethodsFixture(false, true);
  dashboard.paymentSetup.paymentMethodReadinessReady = true;
  dashboard.paymentSetup.paymentMethodReadinessStatusLabel = "Ready";
  dashboard.paymentSetup.readyPaymentMethodCount = 1;
  dashboard.paymentSetup.readyPaymentMethodIds = ["qr_manual_payments"];
  dashboard.paymentSetup.paymentMethods = methods;
  dashboard.paymentSetup.providerPaymentMethod = methods[0];
  dashboard.paymentSetup.manualPaymentMethod = methods[1];

  const model = buildOrganizerHomeReadModel(dashboard, [
    workspaceTripFixture(),
  ]);
  const paymentSetup = model.setupGuide.find(
    (item) => item.id === "payment_setup",
  );
  const paymentTile = model.summaryTiles.find(
    (item) => item.id === "payment_method_readiness",
  );

  assert.equal(paymentSetup?.tone, "clear");
  assert.equal(
    paymentSetup?.body,
    "Manual Payments ready; Razorpay online payments: Online Payment Readiness blocked",
  );
  assert.equal(paymentTile?.value, "Ready");
  assert.equal(paymentTile?.detail, paymentSetup?.body);
});

test("Organizer Home exposes existing Trip summaries and available blockers", () => {
  const model = buildOrganizerHomeReadModel(
    dashboardFixture({
      role: "owner",
      tripsCount: 2,
      activeSummaries: [
        latestTripFixture({
          id: 7,
          title: "Spiti Field Week",
          pendingManualPayments: 2,
          launchReady: false,
        }),
        latestTripFixture({
          id: 8,
          title: "Kaza Autumn Run",
          overdueAmountInr: 125000,
          missingRequirements: 3,
          launchReady: true,
        }),
      ],
      attentionItems: [
        attentionFixture({
          id: "trip-7-payment-approvals",
          kind: "payment_approvals",
          tripId: 7,
          tripTitle: "Spiti Field Week",
          count: 2,
        }),
        attentionFixture({
          id: "trip-8-overdue-balances",
          kind: "overdue_balances",
          tripId: 8,
          tripTitle: "Kaza Autumn Run",
          amountInr: 125000,
        }),
        attentionFixture({
          id: "trip-8-missing-requirements",
          kind: "missing_requirements",
          tripId: 8,
          tripTitle: "Kaza Autumn Run",
          count: 3,
        }),
        attentionFixture({
          id: "trip-7-launch-blocker",
          kind: "launch_blocker",
          tripId: 7,
          tripTitle: "Spiti Field Week",
          tone: "blocked",
        }),
      ],
      latestTrip: latestTripFixture({
        pendingManualPayments: 2,
        overdueAmountInr: 125000,
        missingRequirements: 3,
        launchReady: false,
      }),
    }),
    [workspaceTripFixture()],
  );

  assert.equal(model.hasTrips, true);
  assert.equal(model.primaryAction.title, "Create another Trip");
  assert.equal(
    model.tripSummaries[0]?.overviewHref,
    "/operations/trips/7/overview",
  );
  assert.deepEqual(
    model.tripSummaries[0]?.statusChips.map((chip) => [chip.label, chip.tone]),
    [
      ["Published page", "clear"],
      ["Closed booking", "attention"],
      ["18/24 seats", "clear"],
      ["2 approvals", "attention"],
      ["Launch blocked", "blocked"],
    ],
  );
  assert.deepEqual(
    model.attentionItems.map((item) => [
      item.id,
      item.value,
      item.action?.href ?? null,
    ]),
    [
      [
        "trip-7-payment-approvals",
        "2 for Spiti Field Week",
        "/operations/trips/7/payments",
      ],
      [
        "trip-8-overdue-balances",
        "INR 1,25,000",
        "/operations/trips/8/payments",
      ],
      [
        "trip-8-missing-requirements",
        "3 for Kaza Autumn Run",
        "/operations/trips/8/travelers",
      ],
      [
        "trip-7-launch-blocker",
        "Spiti Field Week",
        "/operations/trips/7/launch",
      ],
    ],
  );
});

test("Organizer Home lets Operators open Trips without Owner-only setup actions", () => {
  const model = buildOrganizerHomeReadModel(
    dashboardFixture({
      role: "operator",
      tripsCount: 1,
      providerPaymentSetupComplete: true,
      latestTrip: latestTripFixture({ launchReady: true }),
    }),
    [workspaceTripFixture()],
  );

  assert.equal(model.hasTrips, true);
  assert.equal(model.primaryAction.action, null);
  assert.equal(
    model.tripSummaries[0]?.overviewHref,
    "/operations/trips/7/overview",
  );
  assert.equal(
    model.setupGuide.every((item) => item.action === null),
    true,
  );
  assert.deepEqual(
    model.attentionItems.map((item) => [item.id, item.value]),
    [["clear", "Clear"]],
  );
});

function dashboardFixture({
  activeSummaries,
  attentionItems = [],
  latestTrip = null,
  providerPaymentSetupComplete = false,
  role,
  tripsCount,
}: {
  activeSummaries?: OperationsDashboard["trips"]["activeSummaries"];
  attentionItems?: OperationsDashboard["trips"]["attentionItems"];
  latestTrip?: OperationsDashboard["trips"]["latest"];
  providerPaymentSetupComplete?: boolean;
  role: "owner" | "operator";
  tripsCount: number;
}): OperationsDashboard {
  return {
    ok: true,
    activeOrganizer: {
      id: 2,
      name: "Himalayan Monsoon Cohort",
      slug: "himalayan-monsoon-cohort",
      identity: {
        identityName: "Himalayan Monsoon Cohort",
        name: "Himalayan Monsoon Cohort",
        whatsappNumber: "",
        whatsappHref: "",
        hasWhatsappNumber: false,
        logoUrl: "",
        logoUploaded: false,
        fallback: {
          initials: "HM",
          label: "Himalayan Monsoon Cohort",
          background: "oklch(0.96 0.024 78)",
          foreground: "oklch(0.36 0.08 62)",
        },
        placeholder: false,
      },
    },
    membership: {
      role,
      label: role === "owner" ? "Owner" : "Operator",
    },
    permissions: {
      canAccessOperationsDashboard: true,
      canManageOrganizerIdentity: role === "owner",
      canManagePaymentSetup: role === "owner",
      canManageTeamAccess: role === "owner",
      canUseOperatorWorkflows: true,
      canPrepareTripContent: role === "owner",
      canPublishTrip: role === "owner",
      canOpenBookingAvailability: role === "owner",
      canCloseBookingAvailability: true,
      canManageTripCapacity: role === "owner",
      canManageTripCommercialTerms: role === "owner",
      canManagePostBookingTripDates: role === "owner",
    },
    paymentSetup: {
      provider: "razorpay",
      providerLabel: "Razorpay",
      providerDisclosure:
        "Razorpay processes provider-confirmed payments and provider verification for the India MVP.",
      payoutStatus: "not_started",
      payoutStatusLabel: "Not started",
      settlementReadinessStatus: providerPaymentSetupComplete
        ? "active"
        : "not_started",
      settlementReadinessStatusLabel: providerPaymentSetupComplete
        ? "Active"
        : "Not started",
      settlementReadinessReady: providerPaymentSetupComplete,
      providerPaymentSetupStatus: providerPaymentSetupComplete
        ? "complete"
        : "not_started",
      providerPaymentSetupStatusLabel: providerPaymentSetupComplete
        ? "Complete"
        : "Not started",
      providerPaymentSetupComplete,
      providerAuthorizationMethod: "oauth",
      providerAuthorizationMethodLabel: "OAuth Provider Authorization",
      providerAuthorizationState: providerPaymentSetupComplete
        ? "authorized"
        : "not_started",
      providerAuthorizationStateLabel: providerPaymentSetupComplete
        ? "Authorized"
        : "Not started",
      onlinePaymentReadinessReady: providerPaymentSetupComplete,
      onlinePaymentReadinessStatusLabel: providerPaymentSetupComplete
        ? "Ready"
        : "Blocked",
      onlinePaymentReadinessBlockerCode: providerPaymentSetupComplete
        ? "ready"
        : "provider_verification_not_verified",
      onlinePaymentReadinessBlockerLabel: providerPaymentSetupComplete
        ? "Ready"
        : "Provider verification not verified",
      onlinePaymentReadinessMessage: providerPaymentSetupComplete
        ? "Online Payment Readiness is ready for public booking."
        : "Online Payment Readiness is blocked.",
      paymentMethodReadinessReady: providerPaymentSetupComplete,
      paymentMethodReadinessStatusLabel: providerPaymentSetupComplete
        ? "Ready"
        : "Blocked",
      readyPaymentMethodCount: providerPaymentSetupComplete ? 1 : 0,
      readyPaymentMethodIds: providerPaymentSetupComplete
        ? ["provider_payments"]
        : [],
      paymentMethods: paymentMethodsFixture(providerPaymentSetupComplete),
      providerPaymentMethod: paymentMethodsFixture(
        providerPaymentSetupComplete,
      )[0],
      manualPaymentMethod: paymentMethodsFixture(
        providerPaymentSetupComplete,
      )[1],
      providerVerificationStatus: providerPaymentSetupComplete
        ? "verified"
        : "not_started",
      providerVerificationStatusLabel: providerPaymentSetupComplete
        ? "Verified"
        : "Not started",
      payoutAccountReady: providerPaymentSetupComplete,
      providerPaymentCapabilityEnabled: providerPaymentSetupComplete,
      providerConnectionState: providerPaymentSetupComplete
        ? "healthy"
        : "unhealthy",
      providerConnectionStateLabel: providerPaymentSetupComplete
        ? "Healthy"
        : "Unhealthy",
      providerMode: providerPaymentSetupComplete ? "live" : "test",
      providerModeLabel: providerPaymentSetupComplete ? "Live" : "Test",
      providerOrderCreationAvailable: providerPaymentSetupComplete,
      manualPaymentCapabilityEnabled: true,
      canManageManualPaymentInstructions: role === "owner",
      manualPaymentInstructions: {
        ready: false,
        statusLabel: "Missing Payment QR",
        blockerCode: "payment_qr_missing",
        blockerLabel: "Payment QR missing",
        message:
          "Manual Payment Instructions need a Payment QR before Manual Payments can be offered from Launch.",
        paymentQrUploaded: false,
        paymentQrUrl: "",
        originalFilename: "",
        contentType: "",
        fileSize: 0,
        upiId: "",
        accountName: "",
        bankTransferDetails: "",
        canManage: role === "owner",
        updatedAt: "",
      },
      canManageProviderAuthorization: role === "owner",
      paymentSetupAccessMessage:
        role === "owner"
          ? "Owners can review the Razorpay connection and run recovery actions when access changes."
          : "Operators can view readiness blockers and recovery context, but only Owners can manage Provider Authorization.",
      providerAuthorizationActions:
        role === "owner"
          ? [
              {
                id: "connect",
                label: "Connect with Razorpay",
                description:
                  "Start OAuth Provider Authorization on Razorpay-hosted screens.",
                statusLabel: providerPaymentSetupComplete
                  ? "Connected"
                  : "Available",
                enabled: !providerPaymentSetupComplete,
                tone: "primary",
              },
            ]
          : [],
      individualCreatorPaymentPath: {
        title: "Individual Creator Payment Path",
        summary:
          "Creator-led Organizers can connect a provider account that matches how they already collect trip payments.",
        steps: [
          "Publish a Public Trip Page before submitting provider verification.",
          "Use the TripOS Public Trip URL to show where travelers will pay.",
        ],
      },
      providerVerificationUrl: {
        available: true,
        source: "public_trip_url",
        sourceLabel: "TripOS Public Trip URL",
        urlPath: "/trips/himalayan-monsoon-cohort/spiti-field-week",
        tripId: 7,
        tripTitle: "Spiti Field Week",
        statusLabel: "Ready to share",
        message:
          "Use this published TripOS Public Trip URL as the Provider Verification URL.",
      },
      manualPaymentsOnly: {
        supported: true,
        active: !providerPaymentSetupComplete,
        statusLabel: providerPaymentSetupComplete
          ? "Provider payments ready"
          : "Manual Payments Only",
        publicBookingMessage: providerPaymentSetupComplete
          ? "Public Booking can use provider-confirmed payments when booking availability is open."
          : "Public Booking stays closed with Bookings Opening Soon until Online Payment Readiness is ready.",
        manualOperationsMessage:
          "Manual Bookings and Manual Payments remain available in the Operations Dashboard.",
      },
    },
    trips: {
      count: tripsCount,
      activeSummaries: activeSummaries ?? (latestTrip ? [latestTrip] : []),
      attentionItems,
      latest: latestTrip,
    },
  };
}

function latestTripFixture({
  id = 7,
  launchReady,
  missingRequirements = 0,
  overdueAmountInr = 0,
  pendingManualPayments = 0,
  title = "Spiti Field Week",
}: {
  id?: number;
  launchReady: boolean;
  missingRequirements?: number;
  overdueAmountInr?: number;
  pendingManualPayments?: number;
  title?: string;
}): NonNullable<OperationsDashboard["trips"]["latest"]> {
  return {
    id,
    title,
    startDate: "2026-10-10",
    endDate: "2026-10-15",
    capacity: 24,
    publicationState: "published",
    bookingAvailability: "closed",
    effectiveBookingAvailability: "closed",
    availableSeats: 18,
    coreOperationalBookingCount: 4,
    operationalMetrics: {
      unpaidBookings: 0,
      overdueAmountInr,
      pendingManualPayments,
      pendingManualPaymentsSupported: true,
      missingRequirements,
      missingRequirementsSupported: true,
      availableSeats: 18,
      reservedTravelers: 6,
      coreOperationalBookingCount: 4,
      bookingStateCounts: { reserved: 4 },
    },
    bookings: [],
    launchReadiness: {
      ctaEnabled: launchReady,
      ready: launchReady,
      reasonCode: launchReady ? "ready" : "payment_method_readiness_missing",
      requestedSeats: 1,
      publicationReady: true,
      bookingAvailabilityOpen: false,
      paymentMethodReadinessReady: launchReady,
      paymentMethodReadinessStatusLabel: launchReady ? "Ready" : "Blocked",
      readyPaymentMethodCount: launchReady ? 1 : 0,
      readyPaymentMethodIds: launchReady ? ["provider_payments"] : [],
      paymentMethods: paymentMethodsFixture(launchReady),
      providerPaymentMethod: paymentMethodsFixture(launchReady)[0],
      manualPaymentMethod: paymentMethodsFixture(launchReady)[1],
      onlinePaymentReadinessReady: launchReady,
      onlinePaymentReadinessStatusLabel: launchReady ? "Ready" : "Blocked",
      onlinePaymentReadinessMessage: launchReady
        ? "Online Payment Readiness is ready for public booking."
        : "Provider verification must be verified before public booking can open.",
      providerPaymentSetupComplete: launchReady,
      capacityAvailable: true,
      availableSeats: 18,
      activeSeatHolds: 0,
      bookableSeats: 18,
      bookingAvailability: "closed",
      bookingAvailabilityLabel: "Closed",
      effectiveBookingAvailability: "closed",
      effectiveBookingAvailabilityLabel: "Closed",
      availabilityBand: "available",
      availabilityBandLabel: "Available",
      ctaState: launchReady ? "enabled" : "disabled",
      message: launchReady
        ? "Booking can start for this Trip."
        : "Provider verification must be verified before public booking can open.",
    },
  };
}

function attentionFixture({
  amountInr = 0,
  count = 0,
  id,
  kind,
  tone = "attention",
  tripId,
  tripTitle,
}: Pick<
  OperationsDashboard["trips"]["attentionItems"][number],
  "id" | "kind" | "tripId" | "tripTitle"
> &
  Partial<OperationsDashboard["trips"]["attentionItems"][number]>) {
  return {
    amountInr,
    count,
    id,
    kind,
    message: "Review this Trip.",
    tone,
    tripId,
    tripTitle,
  };
}

function paymentMethodsFixture(onlineReady: boolean, manualReady = false) {
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

function workspaceTripFixture(): WorkspaceTrip {
  return {
    id: 7,
    title: "Spiti Field Week",
    startDate: "2026-10-10",
    endDate: "2026-10-15",
    capacity: 24,
    availableSeats: 18,
    publicationState: "published",
    bookingAvailability: "closed",
    manualPaymentAvailability: "closed",
    effectiveBookingAvailability: "closed",
    publicUrlPath: "/trips/himalayan-monsoon-cohort/spiti-field-week",
    paymentSchedule: {
      hasBalanceMilestone: true,
      balanceDueDaysBeforeStart: 14,
      balanceDueDate: "2026-09-26",
      balanceReminderLeadDays: 3,
      reviewed: true,
    },
    confirmationRequirements: {
      travelerDocuments: false,
      travelerIdentityDetails: false,
      travelLogistics: false,
      emergencyContact: false,
      medicalDisclosure: false,
      fullPaymentBeforeConfirmation: false,
      reviewed: true,
    },
    launchReadiness: {
      ctaEnabled: false,
      ready: false,
      reasonCode: "payment_method_readiness_missing",
      requestedSeats: 1,
      publicationReady: true,
      bookingAvailabilityOpen: false,
      paymentMethodReadinessReady: false,
      paymentMethodReadinessStatusLabel: "Blocked",
      readyPaymentMethodCount: 0,
      readyPaymentMethodIds: [],
      paymentMethods: paymentMethodsFixture(false),
      providerPaymentMethod: paymentMethodsFixture(false)[0],
      manualPaymentMethod: paymentMethodsFixture(false)[1],
      onlinePaymentReadinessReady: false,
      onlinePaymentReadinessStatusLabel: "Blocked",
      onlinePaymentReadinessMessage:
        "Provider verification must be verified before public booking can open.",
      providerPaymentSetupComplete: false,
      capacityAvailable: true,
      availableSeats: 18,
      activeSeatHolds: 0,
      bookableSeats: 18,
      bookingAvailability: "closed",
      bookingAvailabilityLabel: "Closed",
      effectiveBookingAvailability: "closed",
      effectiveBookingAvailabilityLabel: "Closed",
      availabilityBand: "available",
      availabilityBandLabel: "Available",
      ctaState: "disabled",
      message:
        "Provider verification must be verified before public booking can open.",
    },
    tripProfilePublicationReadiness: {
      blockers: [],
      encouraged: [],
      blockerCount: 0,
      encouragedCount: 0,
      publishEligible: true,
      lockAcknowledgementRequired: true,
    },
  };
}
