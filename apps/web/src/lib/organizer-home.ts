import type {
  OperationsDashboard,
  OperationsDashboardAttentionItem,
  OperationsDashboardTripSummary as DashboardTripSummary,
} from "./operations-dashboard.ts";
import type { PaymentMethodReadiness } from "./payment-method-readiness.ts";
import { tripWorkspaceHref } from "./operations-workspace.ts";
import type { WorkspaceTrip } from "./workspace.ts";

export type SetupGuideItemId =
  | "organizer_identity"
  | "team_access"
  | "payment_setup"
  | "create_trip";

export type OrganizerHomeTone = "clear" | "attention" | "blocked" | "readonly";

export type OrganizerHomeAction = {
  label: string;
  href: string;
  primary?: boolean;
};

export type OrganizerHomeSetupItem = {
  id: SetupGuideItemId;
  label: string;
  statusLabel: string;
  tone: OrganizerHomeTone;
  body: string;
  action: OrganizerHomeAction | null;
  readOnlyLabel: string;
};

export type OrganizerHomeSummaryTile = {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: OrganizerHomeTone;
};

export type OrganizerHomeAttentionItem = {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: OrganizerHomeTone;
  action: OrganizerHomeAction | null;
};

export type OrganizerHomeTripSummary = {
  id: number;
  title: string;
  dateRange: string;
  availabilitySummary: string;
  capacitySummary: string;
  statusChips: OrganizerHomeStatusChip[];
  overviewHref: string;
};

export type OrganizerHomeStatusChip = {
  label: string;
  tone: OrganizerHomeTone;
};

export type OrganizerHomePrimaryAction = {
  label: string;
  title: string;
  body: string;
  action: OrganizerHomeAction | null;
};

export type OrganizerHomeZeroTripState = {
  title: string;
  body: string;
  action: OrganizerHomeAction | null;
};

export type OrganizerHomeReadModel = {
  isOwner: boolean;
  hasTrips: boolean;
  introBody: string;
  primaryAction: OrganizerHomePrimaryAction;
  setupGuide: OrganizerHomeSetupItem[];
  summaryTiles: OrganizerHomeSummaryTile[];
  attentionItems: OrganizerHomeAttentionItem[];
  tripSummaries: OrganizerHomeTripSummary[];
  zeroTripState: OrganizerHomeZeroTripState;
};

export function buildOrganizerHomeReadModel(
  dashboard: OperationsDashboard,
  trips: WorkspaceTrip[],
): OrganizerHomeReadModel {
  const isOwner = dashboard.membership.role === "owner";
  const hasTrips = dashboard.trips.count > 0 || trips.length > 0;

  return {
    isOwner,
    hasTrips,
    introBody: isOwner
      ? "Setup, Trips, blockers."
      : "Open Trips. Review blockers.",
    primaryAction: buildPrimaryAction({ dashboard, hasTrips, isOwner }),
    setupGuide: buildSetupGuideItems({ dashboard, hasTrips, isOwner }),
    summaryTiles: buildSummaryTiles(dashboard, trips),
    attentionItems: buildAttentionItems({ dashboard, hasTrips, isOwner }),
    tripSummaries: buildTripSummaries(dashboard, trips),
    zeroTripState: buildZeroTripState(isOwner),
  };
}

function buildPrimaryAction({
  dashboard,
  hasTrips,
  isOwner,
}: {
  dashboard: OperationsDashboard;
  hasTrips: boolean;
  isOwner: boolean;
}): OrganizerHomePrimaryAction {
  if (isOwner) {
    return {
      label: "Owner action",
      title: hasTrips ? "Create another Trip" : "Create the first Trip",
      body: "Draft setup available now.",
      action: {
        label: "Create Trip",
        href: "/trips/new",
        primary: true,
      },
    };
  }

  return {
    label: "Operator view",
    title: hasTrips ? "Open a Trip to continue" : "Waiting for an Owner",
    body: hasTrips
      ? "Open existing Trips."
      : `An Owner at ${dashboard.activeOrganizer.name} must create a Trip first.`,
    action: null,
  };
}

function buildSetupGuideItems({
  dashboard,
  hasTrips,
  isOwner,
}: {
  dashboard: OperationsDashboard;
  hasTrips: boolean;
  isOwner: boolean;
}): OrganizerHomeSetupItem[] {
  return [
    buildOrganizerIdentityItem(dashboard, isOwner),
    buildTeamAccessItem(dashboard, isOwner),
    buildPaymentSetupItem(dashboard, isOwner),
    buildCreateTripItem(hasTrips, isOwner),
  ];
}

function buildOrganizerIdentityItem(
  dashboard: OperationsDashboard,
  isOwner: boolean,
): OrganizerHomeSetupItem {
  const needsReview = dashboard.activeOrganizer.identity.placeholder;

  if (!isOwner) {
    return {
      id: "organizer_identity",
      label: "Organizer Identity",
      statusLabel: needsReview ? "Owner-managed" : "Ready",
      tone: needsReview ? "readonly" : "clear",
      body: needsReview
        ? "Owner review needed."
        : `Traveler-facing name: ${dashboard.activeOrganizer.identity.name}.`,
      action: null,
      readOnlyLabel: "Read-only",
    };
  }

  return {
    id: "organizer_identity",
    label: "Organizer Identity",
    statusLabel: needsReview ? "Review" : "Ready",
    tone: needsReview ? "attention" : "clear",
    body: needsReview
      ? "Confirm traveler-facing name."
      : `Traveler-facing name: ${dashboard.activeOrganizer.identity.name}.`,
    action: {
      label: needsReview ? "Review Identity" : "Manage Identity",
      href: "/organizer-identity",
    },
    readOnlyLabel: "",
  };
}

function buildTeamAccessItem(
  dashboard: OperationsDashboard,
  isOwner: boolean,
): OrganizerHomeSetupItem {
  if (!isOwner) {
    return {
      id: "team_access",
      label: "Team Access",
      statusLabel: "Owner-managed",
      tone: "readonly",
      body: "Owner-managed.",
      action: null,
      readOnlyLabel: dashboard.membership.label,
    };
  }

  return {
    id: "team_access",
    label: "Team Access",
    statusLabel: "Available",
    tone: "clear",
    body: "Invite Owners or Operators.",
    action: {
      label: "Open Team Access",
      href: "/team-access",
    },
    readOnlyLabel: "",
  };
}

function buildPaymentSetupItem(
  dashboard: OperationsDashboard,
  isOwner: boolean,
): OrganizerHomeSetupItem {
  const isReady = dashboard.paymentSetup.paymentMethodReadinessReady;
  const statusLabel = dashboard.paymentSetup.paymentMethodReadinessStatusLabel;
  const readinessMessage = paymentMethodSummary(
    dashboard.paymentSetup.paymentMethods,
  );

  if (!isOwner) {
    return {
      id: "payment_setup",
      label: "Payment Setup",
      statusLabel: isReady ? "Ready" : "Owner-managed blocker",
      tone: isReady ? "clear" : "blocked",
      body: readinessMessage,
      action: null,
      readOnlyLabel: statusLabel,
    };
  }

  return {
    id: "payment_setup",
    label: "Payment Setup",
    statusLabel: isReady ? "Ready" : statusLabel,
    tone: isReady ? "clear" : "attention",
    body: readinessMessage,
    action: {
      label: isReady ? "Review Payment Setup" : "Open Payment Setup",
      href: "/payment-setup",
    },
    readOnlyLabel: "",
  };
}

function buildCreateTripItem(
  hasTrips: boolean,
  isOwner: boolean,
): OrganizerHomeSetupItem {
  if (!isOwner) {
    return {
      id: "create_trip",
      label: "Create Trip",
      statusLabel: "Owner-only",
      tone: hasTrips ? "readonly" : "blocked",
      body: hasTrips
        ? "Owners create Trips."
        : "An Owner must create the first Trip before Operator workflows begin.",
      action: null,
      readOnlyLabel: "Owner action required",
    };
  }

  return {
    id: "create_trip",
    label: "Create Trip",
    statusLabel: hasTrips ? "Available" : "Primary next action",
    tone: hasTrips ? "clear" : "attention",
    body: hasTrips
      ? "Create from Trips."
      : "Start the first draft Trip when the offering is ready.",
    action: {
      label: hasTrips ? "Create another Trip" : "Create Trip",
      href: "/trips/new",
      primary: !hasTrips,
    },
    readOnlyLabel: "",
  };
}

function buildSummaryTiles(
  dashboard: OperationsDashboard,
  trips: WorkspaceTrip[],
): OrganizerHomeSummaryTile[] {
  const tripCount = Math.max(dashboard.trips.count, trips.length);
  const totalCapacity = trips.reduce((sum, trip) => sum + trip.capacity, 0);
  const totalAvailableSeats = trips.reduce(
    (sum, trip) => sum + trip.availableSeats,
    0,
  );
  const latestMetrics = dashboard.trips.latest?.operationalMetrics;
  const latestOperationalBookings =
    latestMetrics?.coreOperationalBookingCount ??
    dashboard.trips.latest?.coreOperationalBookingCount ??
    0;

  return [
    {
      id: "trips",
      label: "Trips",
      value: String(tripCount),
      detail: tripCount ? "Open Trip work from Home." : "No Trips yet.",
      tone: tripCount ? "clear" : "attention",
    },
    {
      id: "payment_method_readiness",
      label: "Payment methods",
      value: dashboard.paymentSetup.paymentMethodReadinessStatusLabel,
      detail: paymentMethodSummary(dashboard.paymentSetup.paymentMethods),
      tone: dashboard.paymentSetup.paymentMethodReadinessReady
        ? "clear"
        : "attention",
    },
    {
      id: "available_seats",
      label: "Seats available",
      value: tripCount ? `${totalAvailableSeats}/${totalCapacity}` : "0",
      detail: tripCount
        ? "Across listed Trips."
        : "Create a Trip to set capacity.",
      tone: tripCount ? "clear" : "readonly",
    },
    {
      id: "latest_trip_bookings",
      label: "Latest Trip bookings",
      value: String(latestOperationalBookings),
      detail: dashboard.trips.latest
        ? "Core operational bookings."
        : "No booking activity yet.",
      tone: latestOperationalBookings > 0 ? "attention" : "clear",
    },
  ];
}

function buildAttentionItems({
  dashboard,
  hasTrips,
  isOwner,
}: {
  dashboard: OperationsDashboard;
  hasTrips: boolean;
  isOwner: boolean;
}): OrganizerHomeAttentionItem[] {
  if (!hasTrips) {
    return [
      {
        id: "zero_trips",
        label: "Trip operations",
        value: "No Trips yet",
        detail: isOwner
          ? "Create a draft Trip when the offering is ready."
          : "An Owner must create a Trip before Operator workflows begin.",
        tone: isOwner ? "attention" : "blocked",
        action: null,
      },
    ];
  }

  const items = dashboard.trips.attentionItems.map(buildAttentionItem);

  if (!items.length) {
    items.push({
      id: "clear",
      label: "Needs attention",
      value: "Clear",
      detail: "No launch, payment, or readiness blockers are visible.",
      tone: "clear",
      action: null,
    });
  }

  return items;
}

function buildAttentionItem(
  item: OperationsDashboardAttentionItem,
): OrganizerHomeAttentionItem {
  switch (item.kind) {
    case "payment_approvals":
      return {
        id: item.id,
        label: "Manual Payment approvals",
        value: `${item.count} for ${item.tripTitle}`,
        detail: item.message,
        tone: item.tone,
        action: {
          label: "Open Payments",
          href: tripWorkspaceHref("/payments", item.tripId),
        },
      };
    case "overdue_balances":
      return {
        id: item.id,
        label: "Overdue balances",
        value: formatInr(item.amountInr),
        detail: `${item.tripTitle}: ${item.message}`,
        tone: item.tone,
        action: {
          label: "Open Payments",
          href: tripWorkspaceHref("/payments", item.tripId),
        },
      };
    case "missing_requirements":
      return {
        id: item.id,
        label: "Missing Confirmation Requirements",
        value: `${item.count} for ${item.tripTitle}`,
        detail: item.message,
        tone: item.tone,
        action: {
          label: "Open Travelers",
          href: tripWorkspaceHref("/travelers", item.tripId),
        },
      };
    case "launch_blocker":
      return {
        id: item.id,
        label: "Launch blocker",
        value: item.tripTitle,
        detail: item.message,
        tone: "blocked",
        action: {
          label: "Review Launch",
          href: tripWorkspaceHref("/launch", item.tripId),
        },
      };
  }
}

function buildTripSummaries(
  dashboard: OperationsDashboard,
  trips: WorkspaceTrip[],
): OrganizerHomeTripSummary[] {
  const summariesById = new Map(
    dashboard.trips.activeSummaries.map((summary) => [summary.id, summary]),
  );
  const workspaceSummaries = trips.map((trip) =>
    buildTripSummary(trip, summariesById.get(trip.id)),
  );

  if (workspaceSummaries.length) {
    return workspaceSummaries;
  }

  return dashboard.trips.activeSummaries.map((summary) =>
    buildTripSummary(summary, summary),
  );
}

function buildTripSummary(
  trip: WorkspaceTrip | DashboardTripSummary,
  dashboardSummary?: DashboardTripSummary,
): OrganizerHomeTripSummary {
  return {
    id: trip.id,
    title: trip.title,
    dateRange: `${formatShortDate(trip.startDate)} to ${formatShortDate(
      trip.endDate,
    )}`,
    availabilitySummary: `${titleCase(
      trip.publicationState,
    )} page, ${titleCase(trip.effectiveBookingAvailability)} booking`,
    capacitySummary: `${trip.availableSeats}/${trip.capacity} seats available`,
    statusChips: buildTripStatusChips(trip, dashboardSummary),
    overviewHref: tripWorkspaceHref("/overview", trip.id),
  };
}

function buildTripStatusChips(
  trip: WorkspaceTrip | DashboardTripSummary,
  dashboardSummary?: DashboardTripSummary,
): OrganizerHomeStatusChip[] {
  const chips: OrganizerHomeStatusChip[] = [
    {
      label: `${titleCase(trip.publicationState)} page`,
      tone: trip.publicationState === "published" ? "clear" : "readonly",
    },
    {
      label: `${titleCase(trip.effectiveBookingAvailability)} booking`,
      tone:
        trip.effectiveBookingAvailability === "open" ? "clear" : "attention",
    },
    {
      label: `${trip.availableSeats}/${trip.capacity} seats`,
      tone: trip.availableSeats > 0 ? "clear" : "blocked",
    },
  ];

  if (!dashboardSummary) {
    if (!trip.launchReadiness.ready) {
      chips.push({ label: "Launch blocked", tone: "blocked" });
    }
    return chips;
  }

  const metrics = dashboardSummary.operationalMetrics;
  if (metrics.pendingManualPayments > 0) {
    chips.push({
      label: `${metrics.pendingManualPayments} approvals`,
      tone: "attention",
    });
  }
  if (metrics.overdueAmountInr > 0) {
    chips.push({
      label: `${formatInr(metrics.overdueAmountInr)} overdue`,
      tone: "attention",
    });
  }
  if (metrics.missingRequirements > 0) {
    chips.push({
      label: `${metrics.missingRequirements} missing`,
      tone: "attention",
    });
  }
  if (!dashboardSummary.launchReadiness.ready) {
    chips.push({ label: "Launch blocked", tone: "blocked" });
  }

  return chips;
}

function paymentMethodSummary(methods: PaymentMethodReadiness[]): string {
  if (!methods.length) {
    return "No payment methods are ready for public booking.";
  }

  const ready = methods
    .filter((method) => method.ready)
    .map(paymentMethodLabel);
  const blocked = methods
    .filter((method) => !method.ready)
    .map((method) => {
      const label = paymentMethodLabel(method);
      return method.blockerLabel && method.blockerLabel !== "Blocked"
        ? `${label}: ${method.blockerLabel}`
        : `${label}: blocked`;
    });

  if (ready.length) {
    return [
      `${ready.join(", ")} ready`,
      blocked.length ? blocked.join("; ") : "",
    ]
      .filter(Boolean)
      .join("; ");
  }

  return blocked.join("; ");
}

function paymentMethodLabel(method: PaymentMethodReadiness): string {
  if (method.methodType === "provider_payment") {
    return `${method.providerLabel || "Provider"} online payments`;
  }
  return method.label;
}

function buildZeroTripState(isOwner: boolean): OrganizerHomeZeroTripState {
  if (isOwner) {
    return {
      title: "Create the first Trip when ready",
      body: "Create a draft Trip, then publish in Launch.",
      action: {
        label: "Create Trip",
        href: "/trips/new",
        primary: true,
      },
    };
  }

  return {
    title: "Waiting for an Owner",
    body: "An Owner must create a Trip before operations begin.",
    action: null,
  };
}

function formatShortDate(value: string): string {
  if (!value) {
    return "Date pending";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function formatInr(value: number): string {
  return `INR ${new Intl.NumberFormat("en-IN").format(value)}`;
}

function titleCase(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
