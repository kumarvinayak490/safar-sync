import { drfApiUrl } from "./drf-request.ts";
import { tripWorkspaceHref } from "./operations-workspace.ts";
import type {
  TripOverview,
  TripOverviewBooking,
  TripOverviewManualPayment,
  TripOverviewProviderPayment,
} from "./trip-overview.ts";

export type TripOperationArea =
  | "bookings"
  | "payments"
  | "travelers"
  | "communications"
  | "exports";

export const TRIP_OPERATION_AREAS: Record<
  TripOperationArea,
  { label: string; path: `/${TripOperationArea}` }
> = {
  bookings: { label: "Bookings", path: "/bookings" },
  payments: { label: "Payments", path: "/payments" },
  travelers: { label: "Travelers", path: "/travelers" },
  communications: { label: "Communications", path: "/communications" },
  exports: { label: "Exports", path: "/exports" },
};

export type OperationMetric = {
  label: string;
  value: string;
  detail: string;
  tone: "clear" | "attention" | "blocked" | "readonly";
};

export type TripOperationContext = {
  tripId: number;
  tripTitle: string;
  dateRange: string;
  selectedTripHref: string;
};

export type BookingOperationRow = {
  id: number;
  bookingHref: string;
  bookingContactName: string;
  bookingState: string;
  bookingStateLabel: string;
  paymentState: string;
  paymentStateLabel: string;
  paymentTone: "clear" | "attention" | "blocked" | "readonly";
  travelerSlotCount: string;
  bookingTotal: string;
  reservationAmount: string;
  collectedAmount: string;
  balanceLabel: string;
  balanceTone: "clear" | "attention" | "blocked";
  readinessLabel: string;
  readinessTone: "clear" | "attention";
};

export type BookingsOperationModel = {
  context: TripOperationContext;
  metrics: OperationMetric[];
  rows: BookingOperationRow[];
};

export type PaymentBalanceRow = {
  id: number;
  bookingContactName: string;
  paymentState: string;
  paymentStateLabel: string;
  paymentTone: "clear" | "attention" | "blocked" | "readonly";
  bookingTotal: string;
  collectedAmount: string;
  dueAmount: string;
  balanceLabel: string;
  balanceTone: "clear" | "attention" | "blocked";
  refundDueAmount: string;
};

export type ManualPaymentApprovalRow = {
  id: number;
  bookingContactName: string;
  travelerCountLabel: string;
  packageContext: string;
  sourceLabel: string;
  status: TripOverviewManualPayment["status"];
  statusLabel: string;
  statusTone: "clear" | "attention" | "blocked";
  amount: string;
  referenceLabel: string;
  proofLabel: string;
  proofStatusLabel: string;
  proofSensitivityLabel: string;
  proofDownloadHref: string;
  submittedAtLabel: string;
};

export type ProviderPaymentReconciliationRow = {
  id: string;
  bookingContactName: string;
  providerLabel: string;
  purposeLabel: string;
  grossAmount: string;
  providerFeeAmount: string;
  providerFeeDetail: string;
  providerNetSettlementAmount: string;
  providerNetSettlementDetail: string;
  platformFeeAmount: string;
  platformFeeDetail: string;
  providerReferenceLabel: string;
  confirmedAtLabel: string;
};

export type PaymentsOperationModel = {
  context: TripOperationContext;
  metrics: OperationMetric[];
  balanceRows: PaymentBalanceRow[];
  providerPaymentRows: ProviderPaymentReconciliationRow[];
  manualPaymentRows: ManualPaymentApprovalRow[];
  scopeNote: string;
};

export type TravelerRequirementRow = {
  id: number;
  travelerHref: string;
  bookingContactName: string;
  travelerSlotCount: string;
  bookingStateLabel: string;
  bookingState: string;
  paymentStateLabel: string;
  paymentTone: "clear" | "attention" | "blocked" | "readonly";
  readinessLabel: string;
  readinessTone: "clear" | "attention";
  requirementDetail: string;
};

export type TravelerRequirementCategory = {
  label: string;
  sensitive: boolean;
};

export type TravelersOperationModel = {
  context: TripOperationContext;
  metrics: OperationMetric[];
  requirementRows: TravelerRequirementRow[];
  requirementCategories: TravelerRequirementCategory[];
};

export type CommunicationQueueRow = {
  id: string;
  type: "Reminder" | "Announcement";
  title: string;
  audience: string;
  audienceDetail: string;
  channelLabel: string;
  status: string;
  tone: "clear" | "attention" | "readonly";
};

export type CommunicationsOperationModel = {
  context: TripOperationContext;
  metrics: OperationMetric[];
  queues: CommunicationQueueRow[];
};

export type ExportOption = {
  id: string;
  title: string;
  description: string;
  href: string;
  sensitive: boolean;
  sensitivityLabel: string;
  sensitivityTone: "clear" | "blocked";
  policyLabel: string;
  actionLabel: string;
};

export type ExportsOperationModel = {
  context: TripOperationContext;
  metrics: OperationMetric[];
  options: ExportOption[];
};

export function tripOperationHref(
  area: TripOperationArea,
  tripId: number,
): string {
  return tripWorkspaceHref(TRIP_OPERATION_AREAS[area].path, tripId);
}

export function buildBookingsOperationModel(
  overview: TripOverview,
): BookingsOperationModel {
  const rows = overview.bookingProgress.bookings.map((booking) =>
    bookingOperationRow(overview.trip.id, booking),
  );
  const bookingCounts = overview.bookingProgress.bookingStateCounts;
  const needsReview = rows.filter(
    (row) => row.readinessTone === "attention",
  ).length;

  return {
    context: operationContext(overview, "bookings"),
    metrics: [
      {
        label: "Operational Bookings",
        value: String(overview.bookingProgress.coreOperationalBookingCount),
        detail: bookingStateSummary(bookingCounts),
        tone: rows.length ? "attention" : "readonly",
      },
      {
        label: "Reserved Travelers",
        value: `${overview.capacity.reservedTravelers}/${overview.capacity.totalSeats}`,
        detail: `${overview.capacity.availableSeats} Available Seats`,
        tone: overview.capacity.availableSeats > 0 ? "clear" : "blocked",
      },
      {
        label: "Readiness review",
        value: String(needsReview),
        detail: needsReview
          ? "Bookings need Confirmation Requirements"
          : "No readiness gaps in visible Bookings",
        tone: needsReview ? "attention" : "clear",
      },
    ],
    rows,
  };
}

export function buildPaymentsOperationModel(
  overview: TripOverview,
): PaymentsOperationModel {
  const balanceRows = overview.bookingProgress.bookings.map((booking) =>
    paymentBalanceRow(booking),
  );
  const providerPaymentRows = overview.bookingProgress.bookings.flatMap(
    (booking) =>
      booking.providerPayments.map((payment) =>
        providerPaymentReconciliationRow(booking.bookingContactName, payment),
      ),
  );
  const manualPaymentRows = overview.bookingProgress.bookings.flatMap(
    (booking) =>
      booking.manualPayments
        .filter((payment) => payment.status === "submitted")
        .map((payment) =>
          manualPaymentApprovalRow(booking.bookingContactName, payment),
        ),
  );
  const pendingManualPayments = manualPaymentRows.length;

  return {
    context: operationContext(overview, "payments"),
    metrics: [
      {
        label: "Collected balance",
        value: formatInr(overview.paymentReadiness.collectedInr),
        detail: "Confirmed + approved",
        tone: overview.paymentReadiness.collectedInr ? "clear" : "readonly",
      },
      {
        label: "Due",
        value: formatInr(overview.paymentReadiness.dueInr),
        detail: overview.paymentReadiness.overdueInr
          ? `${formatInr(overview.paymentReadiness.overdueInr)} overdue`
          : "Outstanding balances",
        tone: overview.paymentReadiness.overdueInr
          ? "blocked"
          : overview.paymentReadiness.dueInr
            ? "attention"
            : "clear",
      },
      {
        label: "Provider fees",
        value: formatInr(overview.paymentReadiness.providerFeeAmountInr),
        detail: providerReportedDetail(
          overview.paymentReadiness.providerPaymentsWithFeeCount,
          overview.paymentReadiness.providerPaymentCount,
        ),
        tone: overview.paymentReadiness.providerFeeAmountInr
          ? "attention"
          : "readonly",
      },
      {
        label: "TripOS Platform Fee",
        value: formatInr(overview.paymentReadiness.platformFeeInr),
        detail: "Separate fee",
        tone: overview.paymentReadiness.platformFeeInr ? "readonly" : "clear",
      },
      {
        label: "Manual Payment approvals",
        value: String(pendingManualPayments),
        detail: pendingManualPayments
          ? "Submitted Manual Payments need review"
          : "Approval queue is clear",
        tone: pendingManualPayments ? "attention" : "clear",
      },
      {
        label: "Refund due",
        value: formatInr(overview.paymentReadiness.refundDueInr),
        detail: "Booking-level",
        tone: overview.paymentReadiness.refundDueInr ? "blocked" : "clear",
      },
    ],
    balanceRows,
    providerPaymentRows,
    manualPaymentRows,
    scopeNote:
      "Payments is Trip-level reconciliation. Organizer-level Payment Setup stays outside this Trip workspace. Booking balances use Gross Provider Payment Amount; provider fees, net settlement, and TripOS Platform Fee stay separate.",
  };
}

export function buildTravelersOperationModel(
  overview: TripOverview,
): TravelersOperationModel {
  const requirementRows = overview.bookingProgress.bookings.map((booking) => ({
    id: booking.id,
    travelerHref: `${tripOperationHref("travelers", overview.trip.id)}#traveler-booking-${booking.id}`,
    bookingContactName: booking.bookingContactName,
    travelerSlotCount: pluralize(booking.travelerSlotCount, "Traveler Slot"),
    bookingState: booking.bookingState,
    bookingStateLabel: booking.bookingStateLabel,
    paymentStateLabel: booking.paymentStateLabel,
    paymentTone: paymentStateTone(booking.paymentState),
    readinessLabel: booking.confirmationRequirements.ready
      ? "Ready"
      : `${booking.confirmationRequirements.unmetCount} missing`,
    readinessTone: booking.confirmationRequirements.ready
      ? ("clear" as const)
      : ("attention" as const),
    requirementDetail: booking.confirmationRequirements.ready
      ? "Confirmation Requirements clear"
      : "Review identity, documents, logistics, emergency contact, medical disclosure, and payment",
  }));

  return {
    context: operationContext(overview, "travelers"),
    metrics: [
      {
        label: "Reserved Travelers",
        value: String(overview.travelerReadiness.reservedTravelers),
        detail: "Active Travelers in reserved or confirmed Bookings",
        tone: overview.travelerReadiness.reservedTravelers
          ? "attention"
          : "readonly",
      },
      {
        label: "Missing Confirmation Requirements",
        value: String(overview.travelerReadiness.missingRequirements),
        detail: overview.travelerReadiness.missingRequirementsSupported
          ? "Readiness is surfaced inside Travelers"
          : "Readiness checks are not configured",
        tone: overview.travelerReadiness.missingRequirements
          ? "attention"
          : "clear",
      },
      {
        label: "Traveler readiness",
        value: overview.travelerReadiness.ready ? "Clear" : "Review",
        detail: "No separate Requirements tab in this workspace",
        tone: overview.travelerReadiness.ready ? "clear" : "attention",
      },
    ],
    requirementRows,
    requirementCategories: [
      { label: "Traveler Identity Details", sensitive: false },
      { label: "Traveler Documents", sensitive: true },
      { label: "Travel Logistics", sensitive: false },
      { label: "Emergency Contact", sensitive: false },
      { label: "Medical Disclosure", sensitive: true },
      { label: "Full payment before confirmation", sensitive: false },
    ],
  };
}

export function buildCommunicationsOperationModel(
  overview: TripOverview,
): CommunicationsOperationModel {
  const draftBookings = overview.bookingProgress.bookingStateCounts.draft ?? 0;
  const missingRequirements = overview.travelerReadiness.missingRequirements;
  const activeAudience = overview.travelerReadiness.reservedTravelers;

  return {
    context: operationContext(overview, "communications"),
    metrics: [
      {
        label: "Reminder queues",
        value: String(
          [draftBookings, missingRequirements].filter(Boolean).length,
        ),
        detail: "Trip-scoped prompts only",
        tone: draftBookings || missingRequirements ? "attention" : "clear",
      },
      {
        label: "Announcement audience",
        value: String(activeAudience),
        detail: "Active Travelers plus Booking Contacts",
        tone: activeAudience ? "attention" : "readonly",
      },
      {
        label: "Organizer templates",
        value: "None",
        detail: "Communications stays inside this Trip",
        tone: "readonly",
      },
    ],
    queues: [
      {
        id: "missing-requirements",
        type: "Reminder",
        title: "Missing Requirements Reminder",
        audience: missingRequirements
          ? `${missingRequirements} unmet Confirmation Requirements`
          : "No missing Confirmation Requirements",
        audienceDetail:
          "Booking Contact remains responsible; specific Travelers may receive document reminders when contact details exist.",
        channelLabel: "WhatsApp and email",
        status: missingRequirements ? "Needs send decision" : "Clear",
        tone: missingRequirements ? "attention" : "clear",
      },
      {
        id: "draft-recovery",
        type: "Reminder",
        title: "Draft Recovery Reminder",
        audience: draftBookings
          ? `${draftBookings} Draft Bookings`
          : "No Draft Bookings",
        audienceDetail:
          "Operational reminders exclude Cancelled Bookings and stay tied to existing Booking obligations.",
        channelLabel: "WhatsApp and email",
        status: draftBookings ? "Ready when contact details exist" : "Clear",
        tone: draftBookings ? "attention" : "clear",
      },
      {
        id: "operational-announcement",
        type: "Announcement",
        title: "Trip operations update",
        audience: activeAudience
          ? `${activeAudience} reserved Travelers and Booking Contacts`
          : "Audience appears after Bookings reserve seats",
        audienceDetail:
          "Announcements broadcast Trip operations updates without mirroring WhatsApp group chat.",
        channelLabel: "WhatsApp and email",
        status: "Trip-scoped Announcement",
        tone: activeAudience ? "attention" : "readonly",
      },
    ],
  };
}

export function buildExportsOperationModel({
  organizerId,
  overview,
}: {
  organizerId: number;
  overview: TripOverview;
}): ExportsOperationModel {
  const defaultExportPath = operationalExportPath(
    organizerId,
    overview.trip.id,
  );
  const sensitiveExportPath = `${defaultExportPath}?${new URLSearchParams({
    include_sensitive_traveler_information: "true",
    include_sensitive_payment_information: "true",
  }).toString()}`;

  return {
    context: operationContext(overview, "exports"),
    metrics: [
      {
        label: "Rows by default",
        value: String(overview.capacity.reservedTravelers),
        detail: "Draft and cancelled Bookings stay out of handoffs",
        tone: overview.capacity.reservedTravelers ? "attention" : "readonly",
      },
      {
        label: "Sensitive data default",
        value: "Excluded",
        detail: "Traveler and payment-sensitive fields require explicit choice",
        tone: "clear",
      },
      {
        label: "Handoff scope",
        value: "Trip CSV",
        detail: "Trip-scoped field-team handoff",
        tone: "readonly",
      },
    ],
    options: [
      {
        id: "operational-handoff",
        title: "Operational handoff CSV",
        description:
          "Default trip-scoped handoff for field teams without sensitive columns.",
        href: drfApiUrl(defaultExportPath),
        sensitive: false,
        sensitivityLabel: "Sensitive fields excluded",
        sensitivityTone: "clear",
        policyLabel: "Default Operational Export",
        actionLabel: "Download CSV",
      },
      {
        id: "sensitive-review",
        title: "Sensitive review CSV",
        description:
          "Explicit export that includes sensitive traveler and payment fields for controlled review.",
        href: drfApiUrl(sensitiveExportPath),
        sensitive: true,
        sensitivityLabel: "Sensitive fields included",
        sensitivityTone: "blocked",
        policyLabel: "Explicit sensitive selection",
        actionLabel: "Download explicit CSV",
      },
    ],
  };
}

function operationContext(
  overview: TripOverview,
  area: TripOperationArea,
): TripOperationContext {
  return {
    tripId: overview.trip.id,
    tripTitle: overview.trip.title,
    dateRange: `${formatShortDate(overview.trip.startDate)} to ${formatShortDate(
      overview.trip.endDate,
    )}`,
    selectedTripHref: tripOperationHref(area, overview.trip.id),
  };
}

function bookingOperationRow(
  tripId: number,
  booking: TripOverviewBooking,
): BookingOperationRow {
  const ready = booking.confirmationRequirements.ready;

  return {
    id: booking.id,
    bookingHref: `${tripOperationHref("travelers", tripId)}#traveler-booking-${booking.id}`,
    bookingContactName: booking.bookingContactName,
    bookingState: booking.bookingState,
    bookingStateLabel: booking.bookingStateLabel,
    paymentState: booking.paymentState,
    paymentStateLabel: booking.paymentStateLabel,
    paymentTone: paymentStateTone(booking.paymentState),
    travelerSlotCount: pluralize(booking.travelerSlotCount, "Traveler Slot"),
    bookingTotal: formatInr(booking.bookingTotalInr),
    reservationAmount: formatInr(booking.bookingReservationAmountInr),
    collectedAmount: formatInr(booking.reconciliation.collectedInr),
    balanceLabel: balanceLabel(booking),
    balanceTone: balanceTone(booking),
    readinessLabel: ready
      ? "Ready"
      : `${booking.confirmationRequirements.unmetCount} missing`,
    readinessTone: ready ? "clear" : "attention",
  };
}

function paymentBalanceRow(booking: TripOverviewBooking): PaymentBalanceRow {
  return {
    id: booking.id,
    bookingContactName: booking.bookingContactName,
    paymentState: booking.paymentState,
    paymentStateLabel: booking.paymentStateLabel,
    paymentTone: paymentStateTone(booking.paymentState),
    bookingTotal: formatInr(booking.bookingTotalInr),
    collectedAmount: formatInr(booking.reconciliation.collectedInr),
    dueAmount: formatInr(booking.reconciliation.dueInr),
    balanceLabel: balanceLabel(booking),
    balanceTone: balanceTone(booking),
    refundDueAmount: formatInr(booking.reconciliation.refundDueInr),
  };
}

function manualPaymentApprovalRow(
  bookingContactName: string,
  payment: TripOverviewManualPayment,
): ManualPaymentApprovalRow {
  const paymentBookingContact =
    payment.bookingContactName || bookingContactName;

  return {
    id: payment.id,
    bookingContactName: paymentBookingContact,
    travelerCountLabel: pluralize(payment.travelerCount, "Traveler"),
    packageContext: payment.packageContext,
    sourceLabel: payment.sourceLabel,
    status: payment.status,
    statusLabel: payment.statusLabel,
    statusTone: manualPaymentTone(payment.status),
    amount: formatInr(payment.amountInr),
    referenceLabel: payment.paymentReference || "No reference",
    proofLabel: payment.hasPaymentProof
      ? payment.originalFilename || "Payment Proof attached"
      : "No Payment Proof",
    proofStatusLabel: payment.paymentProofStatusLabel,
    proofSensitivityLabel: payment.isSensitivePaymentInformation
      ? "Sensitive Payment Information"
      : "No sensitive Payment Proof",
    proofDownloadHref: payment.paymentProofDownloadUrl
      ? drfApiUrl(payment.paymentProofDownloadUrl)
      : "",
    submittedAtLabel: formatDateTime(payment.submittedAt),
  };
}

function providerPaymentReconciliationRow(
  bookingContactName: string,
  payment: TripOverviewProviderPayment,
): ProviderPaymentReconciliationRow {
  const providerFeeReported = payment.providerFeeAmountInr !== null;
  const providerNetReported = payment.providerNetSettlementAmountInr !== null;

  return {
    id: `${payment.provider}-${payment.id}`,
    bookingContactName,
    providerLabel: payment.providerLabel,
    purposeLabel: payment.paymentPurposeLabel,
    grossAmount: formatInr(payment.grossAmountInr),
    providerFeeAmount: providerFeeReported
      ? formatInr(payment.providerFeeAmountInr ?? 0)
      : "Not reported",
    providerFeeDetail: providerFeeReported
      ? "Provider Fee Amount"
      : "Provider fee pending",
    providerNetSettlementAmount: providerNetReported
      ? formatInr(payment.providerNetSettlementAmountInr ?? 0)
      : "Not reported",
    providerNetSettlementDetail: providerNetReported
      ? "Provider Net Settlement Amount"
      : "Net settlement pending",
    platformFeeAmount: formatInr(payment.platformFeeInr),
    platformFeeDetail: "TripOS Platform Fee",
    providerReferenceLabel:
      payment.providerPaymentReference || payment.providerAttemptReference,
    confirmedAtLabel: formatDateTime(payment.confirmedAt),
  };
}

function paymentStateTone(
  paymentState: string,
): "clear" | "attention" | "blocked" | "readonly" {
  if (paymentState === "fully_paid" || paymentState === "refunded") {
    return "clear";
  }

  if (paymentState === "overdue" || paymentState === "refund_due") {
    return "blocked";
  }

  if (
    paymentState === "unpaid" ||
    paymentState === "reservation_paid" ||
    paymentState === "partially_paid"
  ) {
    return "attention";
  }

  return "readonly";
}

function manualPaymentTone(
  status: TripOverviewManualPayment["status"],
): "clear" | "attention" | "blocked" {
  if (status === "approved") {
    return "clear";
  }

  return status === "rejected" ? "blocked" : "attention";
}

function balanceTone(
  booking: TripOverviewBooking,
): "clear" | "attention" | "blocked" {
  if (
    booking.reconciliation.overdueInr > 0 ||
    booking.reconciliation.refundDueInr > 0
  ) {
    return "blocked";
  }

  return booking.reconciliation.dueInr > 0 ? "attention" : "clear";
}

function balanceLabel(booking: TripOverviewBooking): string {
  if (booking.reconciliation.refundDueInr > 0) {
    return `${formatInr(booking.reconciliation.refundDueInr)} refund due`;
  }

  if (booking.reconciliation.overdueInr > 0) {
    return `${formatInr(booking.reconciliation.overdueInr)} overdue`;
  }

  if (booking.reconciliation.dueInr > 0) {
    return `${formatInr(booking.reconciliation.dueInr)} due`;
  }

  return "Balance clear";
}

function operationalExportPath(organizerId: number, tripId: number): string {
  return `/api/operations/organizers/${organizerId}/trips/${tripId}/operational-export.csv`;
}

function bookingStateSummary(counts: Record<string, number>): string {
  const summary = [
    ["reserved", "reserved"],
    ["confirmed", "confirmed"],
    ["draft", "draft"],
    ["cancelled", "cancelled"],
  ]
    .map(([key, label]) => (counts[key] ? `${counts[key]} ${label}` : ""))
    .filter(Boolean);

  return summary.length ? summary.join(", ") : "No visible Booking rows";
}

function pluralize(count: number, singular: string): string {
  return `${count} ${count === 1 ? singular : `${singular}s`}`;
}

function providerReportedDetail(
  reportedCount: number,
  providerPaymentCount: number,
): string {
  if (!providerPaymentCount) {
    return "No Provider Payments yet";
  }

  const providerPayments = pluralize(providerPaymentCount, "Provider Payment");
  if (!reportedCount) {
    return `Not reported across ${providerPayments}`;
  }

  return `${reportedCount}/${providerPaymentCount} ${pluralize(
    providerPaymentCount,
    "Provider Payment",
  )} reported`;
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

function formatDateTime(value: string): string {
  if (!value) {
    return "Time unavailable";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatInr(value: number): string {
  return `INR ${new Intl.NumberFormat("en-IN").format(value)}`;
}
