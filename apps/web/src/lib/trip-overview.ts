import { authenticatedServerJsonRequest } from "./drf-request.ts";
import { tripWorkspaceHref } from "./operations-workspace.ts";
import {
  normalizePaymentMethodReadiness,
  type PaymentMethodReadiness,
  type PaymentMethodReadinessApiPayload,
} from "./payment-method-readiness.ts";

export type TripOverviewTone = "clear" | "attention" | "blocked" | "readonly";

export type TripOverview = {
  trip: {
    id: number;
    title: string;
    startDate: string;
    endDate: string;
    publicationState: string;
    publicationStateLabel: string;
    bookingAvailability: string;
    bookingAvailabilityLabel: string;
    publicUrlPath: string;
  };
  capacity: {
    totalSeats: number;
    availableSeats: number;
    reservedTravelers: number;
    coreOperationalBookingCount: number;
  };
  packages: TripOverviewPackage[];
  bookingProgress: {
    coreOperationalBookingCount: number;
    bookingStateCounts: Record<string, number>;
    bookings: TripOverviewBooking[];
  };
  paymentReadiness: {
    providerPaymentSetupComplete: boolean;
    providerPaymentSetupStatusLabel: string;
    onlinePaymentReadinessReady: boolean;
    onlinePaymentReadinessStatusLabel: string;
    onlinePaymentReadinessMessage: string;
    paymentMethodReadinessReady: boolean;
    paymentMethodReadinessStatusLabel: string;
    readyPaymentMethodCount: number;
    readyPaymentMethodIds: string[];
    paymentMethods: PaymentMethodReadiness[];
    providerPaymentMethod: PaymentMethodReadiness;
    manualPaymentMethod: PaymentMethodReadiness;
    collectedInr: number;
    dueInr: number;
    overdueInr: number;
    refundDueInr: number;
    platformFeeInr: number;
    grossProviderPaymentAmountInr: number;
    providerFeeAmountInr: number;
    providerNetSettlementAmountInr: number;
    providerPaymentCount: number;
    providerPaymentsWithFeeCount: number;
    providerPaymentsWithNetSettlementCount: number;
    pendingManualPayments: number;
  };
  travelerReadiness: {
    reservedTravelers: number;
    missingRequirements: number;
    missingRequirementsSupported: boolean;
    ready: boolean;
  };
  launchContext: {
    publicationState: string;
    publicationStateLabel: string;
    bookingAvailability: string;
    bookingAvailabilityLabel: string;
    effectiveBookingAvailability: string;
    effectiveBookingAvailabilityLabel: string;
    message: string;
  };
  recentActivity: TripOverviewActivity[];
};

export type TripOverviewPackage = {
  id: number;
  name: string;
  description: string;
  priceInr: number;
  reservationAmountInr: number;
  position: number;
};

export type TripOverviewBooking = {
  id: number;
  bookingState: string;
  bookingStateLabel: string;
  bookingContactName: string;
  travelerSlotCount: number;
  bookingTotalInr: number;
  bookingReservationAmountInr: number;
  paymentState: string;
  paymentStateLabel: string;
  reconciliation: {
    collectedInr: number;
    dueInr: number;
    overdueInr: number;
    refundDueInr: number;
    platformFeeInr: number;
  };
  confirmationRequirements: {
    ready: boolean;
    unmetCount: number;
  };
  providerPayments: TripOverviewProviderPayment[];
  manualPayments: TripOverviewManualPayment[];
};

export type TripOverviewProviderPayment = {
  id: number;
  provider: string;
  providerLabel: string;
  paymentPurpose: string;
  paymentPurposeLabel: string;
  providerAttemptReference: string;
  providerPaymentReference: string;
  grossAmountInr: number;
  providerFeeAmountInr: number | null;
  providerNetSettlementAmountInr: number | null;
  platformFeeInr: number;
  confirmedAt: string;
};

export type TripOverviewManualPayment = {
  id: number;
  source: string;
  sourceLabel: string;
  status: "submitted" | "approved" | "rejected";
  statusLabel: string;
  amountInr: number;
  paymentReference: string;
  originalFilename: string;
  hasPaymentProof: boolean;
  paymentProofStatusLabel: string;
  paymentProofDownloadUrl: string;
  isSensitivePaymentInformation: boolean;
  excludeFromDefaultExports: boolean;
  bookingContactName: string;
  travelerCount: number;
  packageContext: string;
  submittedAt: string;
};

export type TripOverviewActivity = {
  id: number;
  action: string;
  actionLabel: string;
  bookingId: number | null;
  travelerSlotId: number | null;
  actorEmail: string;
  occurredAt: string;
  metadata: Record<string, unknown>;
};

export type TripOverviewStatusPill = {
  label: string;
  tone: TripOverviewTone;
};

export type TripOverviewLinkedRow = {
  label: string;
  value: string;
  detail: string;
  tone: TripOverviewTone;
  href: string;
};

export type TripOverviewReadModel = {
  dateRange: string;
  statusPills: TripOverviewStatusPill[];
  launchContext: {
    message: string;
    href: string;
    tone: TripOverviewTone;
  };
  paymentRows: TripOverviewLinkedRow[];
  readinessRows: TripOverviewLinkedRow[];
  packageRows: Array<{
    id: number;
    name: string;
    description: string;
    price: string;
    reservationAmount: string;
  }>;
  recentActivity: Array<{
    id: number;
    label: string;
    detail: string;
    occurredAt: string;
  }>;
};

export type TripOverviewUnavailable = {
  ok: false;
  status: "unauthenticated" | "forbidden" | "not_found" | "unreachable";
};

export async function getTripOverview({
  organizerId,
  tripId,
}: {
  organizerId: number;
  tripId: number;
}): Promise<(TripOverview & { ok: true }) | TripOverviewUnavailable> {
  try {
    const result = await authenticatedServerJsonRequest<TripOverviewApiPayload>(
      `/api/operations/organizers/${organizerId}/trips/${tripId}/overview/`,
    );

    if (result.response.status === 401) {
      return { ok: false, status: "unauthenticated" };
    }

    if (result.response.status === 403) {
      return { ok: false, status: "forbidden" };
    }

    if (result.response.status === 404) {
      return { ok: false, status: "not_found" };
    }

    if (!result.response.ok || !result.data) {
      return { ok: false, status: "unreachable" };
    }

    return { ok: true, ...normalizeTripOverview(result.data) };
  } catch {
    return { ok: false, status: "unreachable" };
  }
}

export function buildTripOverviewReadModel(
  overview: TripOverview,
): TripOverviewReadModel {
  const paymentBlocked = !overview.paymentReadiness.paymentMethodReadinessReady;
  const travelerAttention =
    overview.travelerReadiness.missingRequirementsSupported &&
    overview.travelerReadiness.missingRequirements > 0;
  const dateRange = `${formatShortDate(overview.trip.startDate)} to ${formatShortDate(
    overview.trip.endDate,
  )}`;

  return {
    dateRange,
    statusPills: [
      {
        label: `${overview.trip.publicationStateLabel} Public Trip Page`,
        tone:
          overview.trip.publicationState === "published" ? "clear" : "readonly",
      },
      {
        label: `${overview.launchContext.effectiveBookingAvailabilityLabel} Booking Availability`,
        tone:
          overview.launchContext.effectiveBookingAvailability === "open"
            ? "clear"
            : overview.capacity.availableSeats <= 0
              ? "blocked"
              : "readonly",
      },
    ],
    launchContext: {
      message: overview.launchContext.message,
      href: tripWorkspaceHref("/launch", overview.trip.id),
      tone:
        overview.launchContext.effectiveBookingAvailability === "open"
          ? "clear"
          : paymentBlocked
            ? "blocked"
            : "readonly",
    },
    paymentRows: [
      {
        label: "Collected",
        value: formatInr(overview.paymentReadiness.collectedInr),
        detail: `${overview.bookingProgress.coreOperationalBookingCount} bookings`,
        tone: overview.paymentReadiness.collectedInr ? "clear" : "readonly",
        href: tripWorkspaceHref("/payments", overview.trip.id),
      },
      {
        label: "Due",
        value: formatInr(overview.paymentReadiness.dueInr),
        detail: overview.paymentReadiness.overdueInr
          ? `${formatInr(overview.paymentReadiness.overdueInr)} overdue`
          : "Outstanding balances",
        tone: overview.paymentReadiness.dueInr ? "attention" : "clear",
        href: tripWorkspaceHref("/payments", overview.trip.id),
      },
      {
        label: "Manual",
        value: String(overview.paymentReadiness.pendingManualPayments),
        detail: "Pending approval",
        tone: overview.paymentReadiness.pendingManualPayments
          ? "attention"
          : "clear",
        href: tripWorkspaceHref("/payments", overview.trip.id),
      },
      {
        label: "Payment methods",
        value: overview.paymentReadiness.paymentMethodReadinessStatusLabel,
        detail: compactPaymentDetail(overview),
        tone: paymentBlocked ? "blocked" : "clear",
        href: paymentBlocked
          ? tripWorkspaceHref("/launch", overview.trip.id)
          : tripWorkspaceHref("/payments", overview.trip.id),
      },
    ],
    readinessRows: [
      {
        label: "Requirements",
        value: overview.travelerReadiness.missingRequirementsSupported
          ? String(overview.travelerReadiness.missingRequirements)
          : "Pending",
        detail: "Docs, identity, logistics, emergency, medical",
        tone: travelerAttention ? "attention" : "clear",
        href: tripWorkspaceHref("/travelers", overview.trip.id),
      },
      {
        label: "Reserved",
        value: String(overview.travelerReadiness.reservedTravelers),
        detail: `${overview.capacity.availableSeats} seats available`,
        tone: overview.travelerReadiness.reservedTravelers
          ? "attention"
          : "readonly",
        href: tripWorkspaceHref("/travelers", overview.trip.id),
      },
      {
        label: "Confirm",
        value: overview.travelerReadiness.ready ? "Ready" : "Needs review",
        detail: overview.travelerReadiness.ready
          ? "Ready to confirm"
          : "Review requirements",
        tone: overview.travelerReadiness.ready ? "clear" : "attention",
        href: tripWorkspaceHref("/travelers", overview.trip.id),
      },
    ],
    packageRows: overview.packages.map((tripPackage) => ({
      id: tripPackage.id,
      name: tripPackage.name,
      description: tripPackage.description,
      price: formatInr(tripPackage.priceInr),
      reservationAmount: formatInr(tripPackage.reservationAmountInr),
    })),
    recentActivity: overview.recentActivity.map((activity) => ({
      id: activity.id,
      label: activity.actionLabel,
      detail: activity.bookingId
        ? `Booking #${activity.bookingId}`
        : activity.actorEmail || "Trip activity",
      occurredAt: formatDateTime(activity.occurredAt),
    })),
  };
}

function normalizeTripOverview(payload: TripOverviewApiPayload): TripOverview {
  return {
    trip: {
      id: payload.trip?.id ?? 0,
      title: payload.trip?.title ?? "Trip Overview",
      startDate: payload.trip?.start_date ?? "",
      endDate: payload.trip?.end_date ?? "",
      publicationState: payload.trip?.publication_state ?? "draft",
      publicationStateLabel: payload.trip?.publication_state_label ?? "Draft",
      bookingAvailability: payload.trip?.booking_availability ?? "closed",
      bookingAvailabilityLabel:
        payload.trip?.booking_availability_label ?? "Closed",
      publicUrlPath: payload.trip?.public_url_path ?? "",
    },
    capacity: {
      totalSeats: payload.capacity?.total_seats ?? 0,
      availableSeats: payload.capacity?.available_seats ?? 0,
      reservedTravelers: payload.capacity?.reserved_travelers ?? 0,
      coreOperationalBookingCount:
        payload.capacity?.core_operational_booking_count ?? 0,
    },
    packages: payload.packages?.map(normalizeTripOverviewPackage) ?? [],
    bookingProgress: {
      coreOperationalBookingCount:
        payload.booking_progress?.core_operational_booking_count ?? 0,
      bookingStateCounts: payload.booking_progress?.booking_state_counts ?? {},
      bookings:
        payload.booking_progress?.bookings?.map(normalizeTripOverviewBooking) ??
        [],
    },
    paymentReadiness: normalizeTripOverviewPaymentReadiness(
      payload.payment_readiness,
    ),
    travelerReadiness: {
      reservedTravelers: payload.traveler_readiness?.reserved_travelers ?? 0,
      missingRequirements:
        payload.traveler_readiness?.missing_requirements ?? 0,
      missingRequirementsSupported:
        payload.traveler_readiness?.missing_requirements_supported ?? false,
      ready: payload.traveler_readiness?.ready ?? false,
    },
    launchContext: {
      publicationState:
        payload.launch_context?.publication_state ??
        payload.trip?.publication_state ??
        "draft",
      publicationStateLabel:
        payload.launch_context?.publication_state_label ??
        payload.trip?.publication_state_label ??
        "Draft",
      bookingAvailability:
        payload.launch_context?.booking_availability ??
        payload.trip?.booking_availability ??
        "closed",
      bookingAvailabilityLabel:
        payload.launch_context?.booking_availability_label ??
        payload.trip?.booking_availability_label ??
        "Closed",
      effectiveBookingAvailability:
        payload.launch_context?.effective_booking_availability ?? "closed",
      effectiveBookingAvailabilityLabel:
        payload.launch_context?.effective_booking_availability_label ??
        "Closed",
      message: payload.launch_context?.message ?? "Booking is not available.",
    },
    recentActivity:
      payload.recent_activity?.map(normalizeTripOverviewActivity) ?? [],
  };
}

function normalizeTripOverviewPaymentReadiness(
  payload?: TripOverviewPaymentReadinessApiPayload,
): TripOverview["paymentReadiness"] {
  const paymentMethodReadiness = normalizePaymentMethodReadiness(payload);
  return {
    providerPaymentSetupComplete:
      payload?.provider_payment_setup_complete ?? false,
    providerPaymentSetupStatusLabel:
      payload?.provider_payment_setup_status_label ?? "Not started",
    onlinePaymentReadinessReady:
      payload?.online_payment_readiness_ready ??
      payload?.provider_payment_setup_complete ??
      false,
    onlinePaymentReadinessStatusLabel:
      payload?.online_payment_readiness_status_label ??
      (payload?.provider_payment_setup_complete ? "Ready" : "Blocked"),
    onlinePaymentReadinessMessage:
      payload?.online_payment_readiness_message ??
      (payload?.provider_payment_setup_complete
        ? "Online Payment Readiness is ready for public booking."
        : "Online Payment Readiness is blocked."),
    paymentMethodReadinessReady: paymentMethodReadiness.ready,
    paymentMethodReadinessStatusLabel: paymentMethodReadiness.statusLabel,
    readyPaymentMethodCount: paymentMethodReadiness.readyMethodCount,
    readyPaymentMethodIds: paymentMethodReadiness.readyMethodIds,
    paymentMethods: paymentMethodReadiness.methods,
    providerPaymentMethod: paymentMethodReadiness.providerPaymentMethod,
    manualPaymentMethod: paymentMethodReadiness.manualPaymentMethod,
    collectedInr: payload?.collected_inr ?? 0,
    dueInr: payload?.due_inr ?? 0,
    overdueInr: payload?.overdue_inr ?? 0,
    refundDueInr: payload?.refund_due_inr ?? 0,
    platformFeeInr: payload?.platform_fee_inr ?? 0,
    grossProviderPaymentAmountInr:
      payload?.gross_provider_payment_amount_inr ?? 0,
    providerFeeAmountInr: payload?.provider_fee_amount_inr ?? 0,
    providerNetSettlementAmountInr:
      payload?.provider_net_settlement_amount_inr ?? 0,
    providerPaymentCount: payload?.provider_payment_count ?? 0,
    providerPaymentsWithFeeCount:
      payload?.provider_payments_with_fee_count ?? 0,
    providerPaymentsWithNetSettlementCount:
      payload?.provider_payments_with_net_settlement_count ?? 0,
    pendingManualPayments: payload?.pending_manual_payments ?? 0,
  };
}

function normalizeTripOverviewPackage(
  payload: TripOverviewPackageApiPayload,
): TripOverviewPackage {
  return {
    id: payload.id ?? 0,
    name: payload.name ?? "Package",
    description: payload.description ?? "",
    priceInr: payload.price_inr ?? 0,
    reservationAmountInr: payload.reservation_amount_inr ?? 0,
    position: payload.position ?? 0,
  };
}

function normalizeTripOverviewBooking(
  payload: TripOverviewBookingApiPayload,
): TripOverviewBooking {
  return {
    id: payload.id ?? 0,
    bookingState: payload.booking_state ?? "draft",
    bookingStateLabel: payload.booking_state_label ?? "Draft",
    bookingContactName: payload.booking_contact_name ?? "Booking Contact",
    travelerSlotCount: payload.traveler_slot_count ?? 0,
    bookingTotalInr: payload.booking_total_inr ?? 0,
    bookingReservationAmountInr: payload.booking_reservation_amount_inr ?? 0,
    paymentState: payload.payment_state ?? "unpaid",
    paymentStateLabel: payload.payment_state_label ?? "Unpaid",
    reconciliation: {
      collectedInr: payload.reconciliation?.collected_inr ?? 0,
      dueInr: payload.reconciliation?.due_inr ?? 0,
      overdueInr: payload.reconciliation?.overdue_inr ?? 0,
      refundDueInr: payload.reconciliation?.refund_due_inr ?? 0,
      platformFeeInr: payload.reconciliation?.platform_fee_inr ?? 0,
    },
    confirmationRequirements: {
      ready: payload.confirmation_requirements?.ready ?? false,
      unmetCount: payload.confirmation_requirements?.unmet_count ?? 0,
    },
    providerPayments:
      payload.provider_payments?.map(normalizeTripOverviewProviderPayment) ??
      [],
    manualPayments:
      payload.manual_payments?.map(normalizeTripOverviewManualPayment) ?? [],
  };
}

function normalizeTripOverviewProviderPayment(
  payload: TripOverviewProviderPaymentApiPayload,
): TripOverviewProviderPayment {
  return {
    id: payload.id ?? 0,
    provider: payload.provider ?? "razorpay",
    providerLabel: payload.provider_label ?? "Provider",
    paymentPurpose: payload.payment_purpose ?? "reservation",
    paymentPurposeLabel: payload.payment_purpose_label ?? "Reservation",
    providerAttemptReference: payload.provider_attempt_reference ?? "",
    providerPaymentReference: payload.provider_payment_reference ?? "",
    grossAmountInr: payload.gross_amount_inr ?? 0,
    providerFeeAmountInr: payload.provider_fee_amount_inr ?? null,
    providerNetSettlementAmountInr:
      payload.provider_net_settlement_amount_inr ?? null,
    platformFeeInr: payload.platform_fee_inr ?? 0,
    confirmedAt: payload.confirmed_at ?? "",
  };
}

function normalizeTripOverviewManualPayment(
  payload: TripOverviewManualPaymentApiPayload,
): TripOverviewManualPayment {
  const status = payload.status ?? "submitted";

  return {
    id: payload.id ?? 0,
    source: payload.source ?? "traveler_submitted",
    sourceLabel: payload.source_label ?? "Traveler-submitted",
    status: isManualPaymentStatus(status) ? status : "submitted",
    statusLabel: payload.status_label ?? "Submitted",
    amountInr: payload.amount_inr ?? 0,
    paymentReference: payload.payment_reference ?? "",
    originalFilename: payload.original_filename ?? "",
    hasPaymentProof: payload.has_payment_proof ?? false,
    paymentProofStatusLabel:
      payload.payment_proof_status_label ??
      (payload.has_payment_proof
        ? "Payment Proof attached"
        : "No Payment Proof"),
    paymentProofDownloadUrl: payload.payment_proof_download_url ?? "",
    isSensitivePaymentInformation:
      payload.is_sensitive_payment_information ?? false,
    excludeFromDefaultExports: payload.exclude_from_default_exports ?? false,
    bookingContactName: payload.booking_contact_name ?? "",
    travelerCount: payload.traveler_count ?? 0,
    packageContext: payload.package_context ?? "Package context unavailable",
    submittedAt: payload.submitted_at ?? "",
  };
}

function isManualPaymentStatus(
  status: string,
): status is TripOverviewManualPayment["status"] {
  return (
    status === "submitted" || status === "approved" || status === "rejected"
  );
}

function normalizeTripOverviewActivity(
  payload: TripOverviewActivityApiPayload,
): TripOverviewActivity {
  return {
    id: payload.id ?? 0,
    action: payload.action ?? "activity",
    actionLabel: payload.action_label ?? "Trip activity",
    bookingId: payload.booking_id ?? null,
    travelerSlotId: payload.traveler_slot_id ?? null,
    actorEmail: payload.actor_email ?? "",
    occurredAt: payload.occurred_at ?? "",
    metadata: payload.metadata ?? {},
  };
}

function compactPaymentDetail(overview: TripOverview): string {
  const methodSummary = paymentMethodDetail(overview);

  if (!overview.paymentReadiness.paymentMethodReadinessReady) {
    return methodSummary || "No payment methods are ready for public booking.";
  }

  const attention = [
    overview.paymentReadiness.pendingManualPayments
      ? `${overview.paymentReadiness.pendingManualPayments} manual pending`
      : "",
    overview.paymentReadiness.overdueInr
      ? `${formatInr(overview.paymentReadiness.overdueInr)} overdue`
      : "",
    overview.paymentReadiness.dueInr
      ? `${formatInr(overview.paymentReadiness.dueInr)} due`
      : "",
  ].filter(Boolean);

  return attention.length
    ? attention.join(", ")
    : methodSummary ||
        `${overview.paymentReadiness.readyPaymentMethodCount} ready for public booking`;
}

function paymentMethodDetail(overview: TripOverview): string {
  const methods = overview.paymentReadiness.paymentMethods;
  if (!methods.length) {
    return "";
  }

  const ready = methods.filter((method) => method.ready);
  const blocked = methods.filter((method) => !method.ready);
  const readyLabels = ready.map(paymentMethodLabel);
  const blockedLabels = blocked.map((method) => {
    const label = paymentMethodLabel(method);
    return method.blockerLabel && method.blockerLabel !== "Blocked"
      ? `${label}: ${method.blockerLabel}`
      : `${label}: blocked`;
  });

  if (readyLabels.length) {
    return [
      `${readyLabels.join(", ")} ready`,
      blockedLabels.length ? blockedLabels.join("; ") : "",
    ]
      .filter(Boolean)
      .join("; ");
  }

  return blockedLabels.join("; ");
}

function paymentMethodLabel(method: PaymentMethodReadiness): string {
  if (method.methodType === "provider_payment") {
    return `${method.providerLabel || "Provider"} online payments`;
  }
  return method.label;
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

type TripOverviewApiPayload = {
  trip?: {
    id?: number;
    title?: string;
    start_date?: string;
    end_date?: string;
    publication_state?: string;
    publication_state_label?: string;
    booking_availability?: string;
    booking_availability_label?: string;
    public_url_path?: string;
  };
  capacity?: {
    total_seats?: number;
    available_seats?: number;
    reserved_travelers?: number;
    core_operational_booking_count?: number;
  };
  packages?: TripOverviewPackageApiPayload[];
  booking_progress?: {
    core_operational_booking_count?: number;
    booking_state_counts?: Record<string, number>;
    bookings?: TripOverviewBookingApiPayload[];
  };
  payment_readiness?: TripOverviewPaymentReadinessApiPayload;
  traveler_readiness?: {
    reserved_travelers?: number;
    missing_requirements?: number;
    missing_requirements_supported?: boolean;
    ready?: boolean;
  };
  launch_context?: {
    publication_state?: string;
    publication_state_label?: string;
    booking_availability?: string;
    booking_availability_label?: string;
    effective_booking_availability?: string;
    effective_booking_availability_label?: string;
    message?: string;
  };
  recent_activity?: TripOverviewActivityApiPayload[];
};

type TripOverviewPaymentReadinessApiPayload =
  PaymentMethodReadinessApiPayload & {
    provider_payment_setup_complete?: boolean;
    provider_payment_setup_status_label?: string;
    online_payment_readiness_ready?: boolean;
    online_payment_readiness_status_label?: string;
    online_payment_readiness_message?: string;
    collected_inr?: number;
    due_inr?: number;
    overdue_inr?: number;
    refund_due_inr?: number;
    platform_fee_inr?: number;
    gross_provider_payment_amount_inr?: number;
    provider_fee_amount_inr?: number;
    provider_net_settlement_amount_inr?: number;
    provider_payment_count?: number;
    provider_payments_with_fee_count?: number;
    provider_payments_with_net_settlement_count?: number;
    pending_manual_payments?: number;
  };

type TripOverviewPackageApiPayload = {
  id?: number;
  name?: string;
  description?: string;
  price_inr?: number;
  reservation_amount_inr?: number;
  position?: number;
};

type TripOverviewBookingApiPayload = {
  id?: number;
  booking_state?: string;
  booking_state_label?: string;
  booking_contact_name?: string;
  traveler_slot_count?: number;
  booking_total_inr?: number;
  booking_reservation_amount_inr?: number;
  payment_state?: string;
  payment_state_label?: string;
  reconciliation?: {
    collected_inr?: number;
    due_inr?: number;
    overdue_inr?: number;
    refund_due_inr?: number;
    platform_fee_inr?: number;
  };
  confirmation_requirements?: {
    ready?: boolean;
    unmet_count?: number;
  };
  provider_payments?: TripOverviewProviderPaymentApiPayload[];
  manual_payments?: TripOverviewManualPaymentApiPayload[];
};

type TripOverviewProviderPaymentApiPayload = {
  id?: number;
  provider?: string;
  provider_label?: string;
  payment_purpose?: string;
  payment_purpose_label?: string;
  provider_attempt_reference?: string;
  provider_payment_reference?: string;
  gross_amount_inr?: number;
  provider_fee_amount_inr?: number | null;
  provider_net_settlement_amount_inr?: number | null;
  platform_fee_inr?: number;
  confirmed_at?: string;
};

type TripOverviewManualPaymentApiPayload = {
  id?: number;
  source?: string;
  source_label?: string;
  status?: string;
  status_label?: string;
  amount_inr?: number;
  payment_reference?: string;
  original_filename?: string;
  has_payment_proof?: boolean;
  payment_proof_status_label?: string;
  payment_proof_download_url?: string;
  is_sensitive_payment_information?: boolean;
  exclude_from_default_exports?: boolean;
  booking_contact_name?: string;
  traveler_count?: number;
  package_context?: string;
  submitted_at?: string;
};

type TripOverviewActivityApiPayload = {
  id?: number;
  action?: string;
  action_label?: string;
  booking_id?: number | null;
  traveler_slot_id?: number | null;
  actor_email?: string;
  occurred_at?: string;
  metadata?: Record<string, unknown>;
};
