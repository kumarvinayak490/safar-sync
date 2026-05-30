import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";

import {
  ORGANIZER_NAV_ITEMS,
  TRIP_WORKSPACE_NAV_ITEMS,
  buildOperationsNavigation,
  buildOperationsShellProps,
  canCreateTrips,
  isTripWorkspaceSection,
  operationsHref,
  parseTripWorkspaceTripId,
  resolveTripWorkspaceSelectedTrip,
  tripWorkspaceCurrentPath,
  tripWorkspaceHref,
  tripWorkspaceSectionPath,
} from "./operations-workspace.ts";
import {
  canPublishPublicTripPage,
  isPublicTripPagePublished,
  publicTripPagePublishDisabledReason,
  type WorkspaceTrip,
} from "./workspace.ts";

test("Operations Workspace selected Trip is resolved only from canonical route params", () => {
  const trips = [
    workspaceTrip(4, "Western Ghats Weekend"),
    workspaceTrip(7, "Spiti Field Week"),
  ];

  assert.equal(parseTripWorkspaceTripId("7"), 7);
  assert.equal(parseTripWorkspaceTripId("not-a-trip"), null);
  assert.equal(parseTripWorkspaceTripId("7.0"), null);
  assert.equal(parseTripWorkspaceTripId("0"), null);
  assert.equal(resolveTripWorkspaceSelectedTrip(trips, 7)?.id, 7);
  assert.equal(resolveTripWorkspaceSelectedTrip(trips, 999), null);
  assert.equal(resolveTripWorkspaceSelectedTrip([], 7), null);
});

test("Operations Workspace navigation builds canonical private Trip URLs", () => {
  const selectedTrip = workspaceTrip(7, "Spiti Field Week");

  assert.equal(
    operationsHref("/payments", selectedTrip),
    "/operations/trips/7/payments",
  );
  assert.equal(
    operationsHref("/overview", selectedTrip),
    "/operations/trips/7/overview",
  );
  assert.equal(
    operationsHref("/payment-setup", selectedTrip),
    "/payment-setup",
  );
  assert.equal(operationsHref("/payments", null), "/trips");
  assert.equal(tripWorkspaceHref("/launch", 7), "/operations/trips/7/launch");
  assert.equal(
    tripWorkspaceCurrentPath(7, "payments"),
    "/operations/trips/7/payments",
  );
  assert.equal(tripWorkspaceSectionPath("travelers"), "/travelers");
});

test("Operations Dashboard has stable Organizer and Trip workspace nav labels", () => {
  assert.deepEqual(
    ORGANIZER_NAV_ITEMS.map((item) => item.label),
    ["Home", "Organizer Identity", "Team Access", "Payment Setup", "Trips"],
  );
  assert.deepEqual(
    TRIP_WORKSPACE_NAV_ITEMS.map((item) => item.label),
    [
      "Overview",
      "Trip Profile",
      "Launch",
      "Bookings",
      "Payments",
      "Travelers",
      "Communications",
      "Exports",
    ],
  );
});

test("Operations Dashboard recognizes only supported Trip workspace sections", () => {
  assert.equal(isTripWorkspaceSection("overview"), true);
  assert.equal(isTripWorkspaceSection("trip-profile"), true);
  assert.equal(isTripWorkspaceSection("payments"), true);
  assert.equal(isTripWorkspaceSection("requirements"), false);
});

test("Root-level Trip Workspace route pages are not first-class product routes", () => {
  for (const section of [
    "overview",
    "trip-profile",
    "launch",
    "bookings",
    "payments",
    "travelers",
    "communications",
    "exports",
  ]) {
    assert.equal(
      existsSync(new URL(`../app/${section}/page.tsx`, import.meta.url)),
      false,
      `${section} should render only under /operations/trips/{tripId}/${section}`,
    );
  }
});

test("Operations Dashboard navigation keeps zero-Trip Organizer state in the Organizer layer", () => {
  const workspace = workspaceContext({
    role: "operator",
    selectedTrip: null,
    trips: [],
  });

  const navigation = buildOperationsNavigation(workspace, {
    activePath: "/home",
    currentPath: "/home",
  });

  assert.equal(navigation.isTripWorkspaceRoute, false);
  assert.equal(navigation.showTripWorkspaceNav, false);
  assert.deepEqual(
    navigation.organizerNav.map((item) => ({
      label: item.label,
      href: item.href,
      active: item.active,
      disabled: item.disabled,
    })),
    [
      { label: "Home", href: "/home", active: true, disabled: false },
      {
        label: "Organizer Identity",
        href: "/organizer-identity",
        active: false,
        disabled: false,
      },
      {
        label: "Team Access",
        href: "/team-access",
        active: false,
        disabled: false,
      },
      {
        label: "Payment Setup",
        href: "/payment-setup",
        active: false,
        disabled: false,
      },
      { label: "Trips", href: "/trips", active: false, disabled: false },
    ],
  );
  assert.deepEqual(navigation.tripNav, []);
});

test("Operations Dashboard Trip workspace nav appears only for a selected Trip workspace route", () => {
  const selectedTrip = workspaceTrip(7, "Spiti Field Week");
  const workspace = workspaceContext({
    role: "owner",
    selectedTrip,
    trips: [workspaceTrip(4, "Western Ghats Weekend"), selectedTrip],
  });

  const organizerNavigation = buildOperationsNavigation(workspace, {
    activePath: "/trips",
    currentPath: "/trips",
  });
  assert.equal(organizerNavigation.isTripWorkspaceRoute, false);
  assert.equal(organizerNavigation.showTripWorkspaceNav, false);
  assert.deepEqual(organizerNavigation.tripNav, []);

  const tripNavigation = buildOperationsNavigation(workspace, {
    activePath: "/payments",
    currentPath: "/payments",
  });
  assert.equal(tripNavigation.isTripWorkspaceRoute, true);
  assert.equal(tripNavigation.showTripWorkspaceNav, true);
  assert.equal(
    tripNavigation.organizerNav.some((item) => item.active),
    false,
  );
  assert.deepEqual(
    tripNavigation.tripNav.map((item) => ({
      label: item.label,
      href: item.href,
      active: item.active,
    })),
    [
      {
        label: "Overview",
        href: "/operations/trips/7/overview",
        active: false,
      },
      {
        label: "Trip Profile",
        href: "/operations/trips/7/trip-profile",
        active: false,
      },
      {
        label: "Launch",
        href: "/operations/trips/7/launch",
        active: false,
      },
      {
        label: "Bookings",
        href: "/operations/trips/7/bookings",
        active: false,
      },
      {
        label: "Payments",
        href: "/operations/trips/7/payments",
        active: true,
      },
      {
        label: "Travelers",
        href: "/operations/trips/7/travelers",
        active: false,
      },
      {
        label: "Communications",
        href: "/operations/trips/7/communications",
        active: false,
      },
      {
        label: "Exports",
        href: "/operations/trips/7/exports",
        active: false,
      },
    ],
  );
});

test("Trip workspace switcher preserves the active section", () => {
  const nextTrip = workspaceTrip(9, "Zanskar Readiness Run");

  assert.equal(
    operationsHref("/payments", nextTrip),
    "/operations/trips/9/payments",
  );
});

test("Operations Dashboard hides Trip workspace nav on Trip routes without a selected Trip", () => {
  const workspace = workspaceContext({
    role: "operator",
    selectedTrip: null,
    trips: [],
  });

  const navigation = buildOperationsNavigation(workspace, {
    activePath: "/launch",
    currentPath: "/launch",
  });

  assert.equal(navigation.isTripWorkspaceRoute, true);
  assert.equal(navigation.showTripWorkspaceNav, false);
  assert.deepEqual(navigation.tripNav, []);
  assert.equal(
    navigation.organizerNav.find((item) => item.path === "/home")?.disabled,
    false,
  );
});

test("Operations Workspace shell props keep route pages thin", () => {
  const trips = [
    workspaceTrip(4, "Western Ghats Weekend"),
    workspaceTrip(7, "Spiti Field Week"),
  ];
  const workspace = {
    organizer: {
      id: 2,
      name: "Himalayan Monsoon Cohort",
      slug: "himalayan-monsoon-cohort",
      membership_role: "owner",
      membership_label: "Owner",
    },
    roleLabel: "Owner",
    selectedTrip: trips[1],
    trips,
  };

  assert.deepEqual(
    buildOperationsShellProps(workspace, {
      activePath: "/bookings",
      currentPath: "/bookings",
    }),
    {
      activePath: "/bookings",
      currentPath: "/bookings",
      navigation: buildOperationsNavigation(workspace, {
        activePath: "/bookings",
        currentPath: "/bookings",
      }),
      organizerId: 2,
      organizerName: "Himalayan Monsoon Cohort",
      roleLabel: "Owner",
      selectedTrip: trips[1],
      trips,
    },
  );
});

test("Operations Workspace shell props allow Organizer context without Trips", () => {
  const workspace = {
    organizer: {
      id: 2,
      name: "Himalayan Monsoon Cohort",
      slug: "himalayan-monsoon-cohort",
      membership_role: "operator",
      membership_label: "Operator",
    },
    roleLabel: "Operator",
    selectedTrip: null,
    trips: [],
  };

  assert.deepEqual(
    buildOperationsShellProps(workspace, {
      activePath: "/home",
      currentPath: "/home",
    }),
    {
      activePath: "/home",
      currentPath: "/home",
      navigation: buildOperationsNavigation(workspace, {
        activePath: "/home",
        currentPath: "/home",
      }),
      organizerId: 2,
      organizerName: "Himalayan Monsoon Cohort",
      roleLabel: "Operator",
      selectedTrip: null,
      trips: [],
    },
  );
});

test("Operations Dashboard exposes Owner-only Trip creation permission", () => {
  assert.equal(
    canCreateTrips(
      workspaceContext({
        role: "owner",
        selectedTrip: null,
        trips: [],
      }),
    ),
    true,
  );
  assert.equal(
    canCreateTrips(
      workspaceContext({
        role: "operator",
        selectedTrip: null,
        trips: [],
      }),
    ),
    false,
  );
});

test("Public Trip Page publish controls enable only for Owner draft with ready profile", () => {
  const draftReadyTrip = {
    ...workspaceTrip(7, "Spiti Field Week"),
    publicationState: "draft",
    launchReadiness: {
      ...workspaceTrip(7, "Spiti Field Week").launchReadiness,
      publicationReady: false,
    },
  };
  const blockedTrip = {
    ...draftReadyTrip,
    tripProfilePublicationReadiness: {
      ...draftReadyTrip.tripProfilePublicationReadiness,
      blockerCount: 1,
      blockers: [
        {
          id: "description",
          label: "Trip Description",
          detail: "Add traveler-facing trip details.",
          sectionId: "description",
          blocking: true,
          tone: "blocked" as const,
        },
      ],
      publishEligible: false,
    },
  };
  const archivedTrip = {
    ...draftReadyTrip,
    publicationState: "archived",
  };

  assert.equal(isPublicTripPagePublished(draftReadyTrip), false);
  assert.equal(
    canPublishPublicTripPage({ roleLabel: "Owner", trip: draftReadyTrip }),
    true,
  );
  assert.equal(
    publicTripPagePublishDisabledReason({
      roleLabel: "Owner",
      trip: draftReadyTrip,
    }),
    undefined,
  );
  assert.equal(
    canPublishPublicTripPage({ roleLabel: "Operator", trip: draftReadyTrip }),
    false,
  );
  assert.equal(
    publicTripPagePublishDisabledReason({
      roleLabel: "Operator",
      trip: draftReadyTrip,
    }),
    "Only Owners can publish the Public Trip Page.",
  );
  assert.equal(
    publicTripPagePublishDisabledReason({
      roleLabel: "Owner",
      trip: blockedTrip,
    }),
    "Resolve Trip Profile Publication Readiness blockers first.",
  );
  assert.equal(
    publicTripPagePublishDisabledReason({
      roleLabel: "Owner",
      trip: archivedTrip,
    }),
    "Only draft Public Trip Pages can be published.",
  );
});

function workspaceTrip(id: number, title: string): WorkspaceTrip {
  return {
    id,
    title,
    startDate: "2026-10-10",
    endDate: "2026-10-15",
    capacity: 24,
    availableSeats: 18,
    publicationState: "published",
    bookingAvailability: "open",
    manualPaymentAvailability: "closed",
    effectiveBookingAvailability: "open",
    publicUrlPath: `/trips/himalayan-monsoon-cohort/${id}`,
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
      ctaEnabled: true,
      ready: true,
      reasonCode: "ready",
      requestedSeats: 1,
      publicationReady: true,
      bookingAvailabilityOpen: true,
      paymentMethodReadinessReady: true,
      paymentMethodReadinessStatusLabel: "Ready",
      readyPaymentMethodCount: 1,
      readyPaymentMethodIds: ["provider_payments"],
      paymentMethods: paymentMethodsFixture(true),
      providerPaymentMethod: paymentMethodsFixture(true)[0],
      manualPaymentMethod: paymentMethodsFixture(true)[1],
      onlinePaymentReadinessReady: true,
      onlinePaymentReadinessStatusLabel: "Ready",
      onlinePaymentReadinessMessage:
        "Online Payment Readiness is ready for public booking.",
      providerPaymentSetupComplete: true,
      capacityAvailable: true,
      availableSeats: 18,
      activeSeatHolds: 0,
      bookableSeats: 18,
      bookingAvailability: "open",
      bookingAvailabilityLabel: "Open",
      effectiveBookingAvailability: "open",
      effectiveBookingAvailabilityLabel: "Open",
      availabilityBand: "available",
      availabilityBandLabel: "Available",
      ctaState: "enabled",
      message: "Booking can start for this trip.",
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

function workspaceContext({
  role,
  selectedTrip,
  trips,
}: {
  role: "owner" | "operator";
  selectedTrip: WorkspaceTrip | null;
  trips: WorkspaceTrip[];
}) {
  const label = role === "owner" ? "Owner" : "Operator";

  return {
    organizer: {
      id: 2,
      name: "Himalayan Monsoon Cohort",
      slug: "himalayan-monsoon-cohort",
      membership_role: role,
      membership_label: label,
    },
    roleLabel: label,
    selectedTrip,
    trips,
  };
}
