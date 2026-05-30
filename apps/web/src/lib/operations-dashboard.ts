import {
  authenticatedServerJsonRequest,
  extractDrfErrorMessage,
} from "@/lib/drf-request";
import {
  normalizeOrganizerIdentity,
  type OrganizerIdentity,
  type OrganizerIdentityApiPayload,
} from "@/lib/organizer-identity";
import {
  normalizePaymentSetupStatus,
  type PaymentSetupStatus,
  type PaymentSetupStatusApiPayload,
} from "@/lib/payment-setup";
import {
  normalizePaymentMethodReadiness,
  type PaymentMethodReadiness,
  type PaymentMethodReadinessApiPayload,
} from "@/lib/payment-method-readiness";

export type OperationsDashboard = {
  ok: true;
  activeOrganizer: {
    id: number;
    name: string;
    slug: string;
    identity: OrganizerIdentity;
  };
  membership: {
    role: "owner" | "operator";
    label: string;
  };
  permissions: {
    canAccessOperationsDashboard: boolean;
    canManageOrganizerIdentity: boolean;
    canManagePaymentSetup: boolean;
    canManageTeamAccess: boolean;
    canUseOperatorWorkflows: boolean;
    canPrepareTripContent: boolean;
    canPublishTrip: boolean;
    canOpenBookingAvailability: boolean;
    canCloseBookingAvailability: boolean;
    canManageTripCapacity: boolean;
    canManageTripCommercialTerms: boolean;
    canManagePostBookingTripDates: boolean;
  };
  paymentSetup: PaymentSetupStatus;
  trips: {
    count: number;
    activeSummaries: OperationsDashboardTripSummary[];
    attentionItems: OperationsDashboardAttentionItem[];
    latest: null | {
      id: number;
      title: string;
      startDate: string;
      endDate: string;
      capacity: number;
      publicationState: string;
      bookingAvailability: string;
      effectiveBookingAvailability: string;
      availableSeats: number;
      coreOperationalBookingCount: number;
      operationalMetrics: OperationalMetrics;
      bookings: OperationsBooking[];
      launchReadiness: {
        ctaEnabled: boolean;
        ready: boolean;
        reasonCode: string;
        requestedSeats: number;
        publicationReady: boolean;
        bookingAvailabilityOpen: boolean;
        paymentMethodReadinessReady: boolean;
        paymentMethodReadinessStatusLabel: string;
        readyPaymentMethodCount: number;
        readyPaymentMethodIds: string[];
        paymentMethods: PaymentMethodReadiness[];
        providerPaymentMethod: PaymentMethodReadiness;
        manualPaymentMethod: PaymentMethodReadiness;
        onlinePaymentReadinessReady: boolean;
        onlinePaymentReadinessStatusLabel: string;
        onlinePaymentReadinessMessage: string;
        providerPaymentSetupComplete: boolean;
        capacityAvailable: boolean;
        availableSeats: number;
        activeSeatHolds: number;
        bookableSeats: number;
        bookingAvailability: string;
        bookingAvailabilityLabel: string;
        effectiveBookingAvailability: string;
        effectiveBookingAvailabilityLabel: string;
        availabilityBand: "available" | "few_seats_left" | "sold_out";
        availabilityBandLabel: string;
        ctaState: "enabled" | "disabled";
        message: string;
      };
    };
  };
};

export type OperationsDashboardTripSummary = {
  id: number;
  title: string;
  startDate: string;
  endDate: string;
  capacity: number;
  publicationState: string;
  bookingAvailability: string;
  effectiveBookingAvailability: string;
  availableSeats: number;
  coreOperationalBookingCount: number;
  operationalMetrics: OperationalMetrics;
  launchReadiness: OperationsDashboardLaunchReadiness;
};

export type OperationsDashboardAttentionKind =
  | "payment_approvals"
  | "overdue_balances"
  | "missing_requirements"
  | "launch_blocker";

export type OperationsDashboardAttentionItem = {
  id: string;
  kind: OperationsDashboardAttentionKind;
  tripId: number;
  tripTitle: string;
  count: number;
  amountInr: number;
  message: string;
  tone: "attention" | "blocked";
};

export type OperationsDashboardLaunchReadiness = {
  ctaEnabled: boolean;
  ready: boolean;
  reasonCode: string;
  requestedSeats: number;
  publicationReady: boolean;
  bookingAvailabilityOpen: boolean;
  paymentMethodReadinessReady: boolean;
  paymentMethodReadinessStatusLabel: string;
  readyPaymentMethodCount: number;
  readyPaymentMethodIds: string[];
  paymentMethods: PaymentMethodReadiness[];
  providerPaymentMethod: PaymentMethodReadiness;
  manualPaymentMethod: PaymentMethodReadiness;
  onlinePaymentReadinessReady: boolean;
  onlinePaymentReadinessStatusLabel: string;
  onlinePaymentReadinessMessage: string;
  providerPaymentSetupComplete: boolean;
  capacityAvailable: boolean;
  availableSeats: number;
  activeSeatHolds: number;
  bookableSeats: number;
  bookingAvailability: string;
  bookingAvailabilityLabel: string;
  effectiveBookingAvailability: string;
  effectiveBookingAvailabilityLabel: string;
  availabilityBand: "available" | "few_seats_left" | "sold_out";
  availabilityBandLabel: string;
  ctaState: "enabled" | "disabled";
  message: string;
};

export type OperationalMetrics = {
  unpaidBookings: number;
  overdueAmountInr: number;
  pendingManualPayments: number;
  pendingManualPaymentsSupported: boolean;
  missingRequirements: number;
  missingRequirementsSupported: boolean;
  availableSeats: number;
  reservedTravelers: number;
  coreOperationalBookingCount: number;
  bookingStateCounts: Record<string, number>;
};

export type OperationsBooking = {
  id: number;
  bookingState: string;
  bookingStateLabel: string;
  bookingContactName: string;
  bookingContactPhone: string;
  bookingContactEmail: string;
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
  };
  confirmationRequirements: {
    ready: boolean;
    unmetCount: number;
    unmet: ConfirmationRequirement[];
  };
  manualPayments: OperationsManualPayment[];
  travelerSlots: OperationsTravelerSlot[];
  attendanceSummary: {
    notMarked: number;
    checkedIn: number;
    noShow: number;
  };
  draftExpiresAt: string;
  createdAt: string;
  updatedAt: string;
};

export type OperationsManualPayment = {
  id: number;
  source: string;
  sourceLabel: string;
  status: "submitted" | "approved" | "rejected";
  statusLabel: string;
  amountInr: number;
  paymentReference: string;
  originalFilename: string;
  hasPaymentProof: boolean;
  isSensitivePaymentInformation: boolean;
  excludeFromDefaultExports: boolean;
  submittedAt: string;
};

export type OperationsTravelerSlot = {
  id: number;
  position: number;
  packageName: string;
  travelerFullName: string;
  travelerPhone: string;
  travelerEmail: string;
  isTraveler: boolean;
  attendanceState: "not_marked" | "checked_in" | "no_show";
  attendanceStateLabel: string;
  attendanceMarkedAt: string | null;
  attendanceMarkedBy: number | null;
  attendanceActionsAvailable: boolean;
};

export type ConfirmationRequirement = {
  code: string;
  label: string;
  scope: string;
  travelerSlotId: number | null;
  travelerSlotPosition: number | null;
};

export type OperationsDashboardUnavailable = {
  ok: false;
  status: "unauthenticated" | "forbidden" | "unreachable";
};

export async function getOperationsDashboard(): Promise<
  OperationsDashboard | OperationsDashboardUnavailable
> {
  try {
    const result =
      await authenticatedServerJsonRequest<OperationsDashboardApiPayload>(
        "/api/operations/dashboard/",
      );

    if (result.response.status === 401) {
      return { ok: false, status: "unauthenticated" };
    }

    if (result.response.status === 403) {
      return { ok: false, status: "forbidden" };
    }

    if (!result.response.ok || !result.data) {
      return { ok: false, status: "unreachable" };
    }

    const payload = result.data;

    const latestTrip = payload.trips?.latest;

    return {
      ok: true,
      activeOrganizer: {
        id: payload.active_organizer?.id ?? 0,
        name: payload.active_organizer?.name ?? "Organizer",
        slug: payload.active_organizer?.slug ?? "organizer",
        identity: normalizeOrganizerIdentity(
          payload.active_organizer?.identity,
          payload.active_organizer?.name ?? "Organizer",
        ),
      },
      membership: {
        role: payload.membership?.role ?? "operator",
        label: payload.membership?.label ?? "Operator",
      },
      permissions: {
        canAccessOperationsDashboard:
          payload.permissions?.can_access_operations_dashboard ?? false,
        canManageOrganizerIdentity:
          payload.permissions?.can_manage_organizer_identity ?? false,
        canManagePaymentSetup:
          payload.permissions?.can_manage_payment_setup ?? false,
        canManageTeamAccess:
          payload.permissions?.can_manage_team_access ?? false,
        canUseOperatorWorkflows:
          payload.permissions?.can_use_operator_workflows ?? false,
        canPrepareTripContent:
          payload.permissions?.can_prepare_trip_content ?? false,
        canPublishTrip: payload.permissions?.can_publish_trip ?? false,
        canOpenBookingAvailability:
          payload.permissions?.can_open_booking_availability ?? false,
        canCloseBookingAvailability:
          payload.permissions?.can_close_booking_availability ?? false,
        canManageTripCapacity:
          payload.permissions?.can_manage_trip_capacity ?? false,
        canManageTripCommercialTerms:
          payload.permissions?.can_manage_trip_commercial_terms ?? false,
        canManagePostBookingTripDates:
          payload.permissions?.can_manage_post_booking_trip_dates ?? false,
      },
      paymentSetup: normalizePaymentSetupStatus(payload.payment_setup),
      trips: {
        count: payload.trips?.count ?? 0,
        activeSummaries:
          payload.trips?.active_summaries?.map(
            normalizeOperationsDashboardTripSummary,
          ) ?? [],
        attentionItems:
          payload.trips?.attention_items?.map(
            normalizeOperationsDashboardAttentionItem,
          ) ?? [],
        latest: latestTrip
          ? {
              ...normalizeOperationsDashboardTripSummary(latestTrip),
              bookings:
                latestTrip.bookings?.map(normalizeOperationsBooking) ?? [],
            }
          : null,
      },
    };
  } catch {
    return { ok: false, status: "unreachable" };
  }
}

type OperationsDashboardApiPayload = {
  active_organizer?: {
    id?: number;
    name?: string;
    slug?: string;
    identity?: OrganizerIdentityApiPayload;
  };
  membership?: {
    role?: "owner" | "operator";
    label?: string;
  };
  permissions?: {
    can_access_operations_dashboard?: boolean;
    can_manage_organizer_identity?: boolean;
    can_manage_payment_setup?: boolean;
    can_manage_team_access?: boolean;
    can_use_operator_workflows?: boolean;
    can_prepare_trip_content?: boolean;
    can_publish_trip?: boolean;
    can_open_booking_availability?: boolean;
    can_close_booking_availability?: boolean;
    can_manage_trip_capacity?: boolean;
    can_manage_trip_commercial_terms?: boolean;
    can_manage_post_booking_trip_dates?: boolean;
  };
  payment_setup?: PaymentSetupStatusApiPayload;
  trips?: {
    count?: number;
    active_summaries?: OperationsDashboardTripApiPayload[];
    attention_items?: OperationsDashboardAttentionApiPayload[];
    latest?: null | {
      id?: number;
      title?: string;
      start_date?: string;
      end_date?: string;
      capacity?: number;
      publication_state?: string;
      booking_availability?: string;
      effective_booking_availability?: string;
      available_seats?: number;
      core_operational_booking_count?: number;
      operational_metrics?: OperationsMetricsApiPayload;
      bookings?: OperationsBookingApiPayload[];
      launch_readiness?: OperationsDashboardLaunchReadinessApiPayload;
    };
  };
};

type OperationsDashboardTripApiPayload = {
  id?: number;
  title?: string;
  start_date?: string;
  end_date?: string;
  capacity?: number;
  publication_state?: string;
  booking_availability?: string;
  effective_booking_availability?: string;
  available_seats?: number;
  core_operational_booking_count?: number;
  operational_metrics?: OperationsMetricsApiPayload;
  launch_readiness?: OperationsDashboardLaunchReadinessApiPayload;
};

type OperationsDashboardAttentionApiPayload = {
  id?: string;
  kind?: OperationsDashboardAttentionKind;
  trip_id?: number;
  trip_title?: string;
  count?: number;
  amount_inr?: number;
  message?: string;
  tone?: "attention" | "blocked";
};

type OperationsDashboardLaunchReadinessApiPayload =
  PaymentMethodReadinessApiPayload & {
    cta_enabled?: boolean;
    ready?: boolean;
    reason_code?: string;
    requested_seats?: number;
    publication_ready?: boolean;
    booking_availability_open?: boolean;
    online_payment_readiness_ready?: boolean;
    online_payment_readiness_status_label?: string;
    online_payment_readiness_message?: string;
    provider_payment_setup_complete?: boolean;
    capacity_available?: boolean;
    available_seats?: number;
    active_seat_holds?: number;
    bookable_seats?: number;
    booking_availability?: string;
    booking_availability_label?: string;
    effective_booking_availability?: string;
    effective_booking_availability_label?: string;
    availability_band?: "available" | "few_seats_left" | "sold_out";
    availability_band_label?: string;
    cta_state?: "enabled" | "disabled";
    message?: string;
  };

type OperationsMetricsApiPayload = {
  unpaid_bookings?: number;
  overdue_amount_inr?: number;
  pending_manual_payments?: number;
  pending_manual_payments_supported?: boolean;
  missing_requirements?: number;
  missing_requirements_supported?: boolean;
  available_seats?: number;
  reserved_travelers?: number;
  core_operational_booking_count?: number;
  booking_state_counts?: Record<string, number>;
};

type OperationsBookingApiPayload = {
  id?: number;
  booking_state?: string;
  booking_state_label?: string;
  booking_contact_name?: string;
  booking_contact_phone?: string;
  booking_contact_email?: string;
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
  };
  confirmation_requirements?: {
    ready?: boolean;
    unmet_count?: number;
    unmet?: {
      code?: string;
      label?: string;
      scope?: string;
      traveler_slot_id?: number | null;
      traveler_slot_position?: number | null;
    }[];
  };
  manual_payments?: OperationsManualPaymentApiPayload[];
  traveler_slots?: OperationsTravelerSlotApiPayload[];
  attendance_summary?: {
    not_marked?: number;
    checked_in?: number;
    no_show?: number;
  };
  draft_expires_at?: string;
  created_at?: string;
  updated_at?: string;
};

type OperationsManualPaymentApiPayload = {
  id?: number;
  source?: string;
  source_label?: string;
  status?: "submitted" | "approved" | "rejected";
  status_label?: string;
  amount_inr?: number;
  payment_reference?: string;
  original_filename?: string;
  has_payment_proof?: boolean;
  is_sensitive_payment_information?: boolean;
  exclude_from_default_exports?: boolean;
  submitted_at?: string;
};

type OperationsTravelerSlotApiPayload = {
  id?: number;
  position?: number;
  package_name?: string;
  traveler_full_name?: string;
  traveler_phone?: string;
  traveler_email?: string;
  is_traveler?: boolean;
  attendance_state?: "not_marked" | "checked_in" | "no_show";
  attendance_state_label?: string;
  attendance_marked_at?: string | null;
  attendance_marked_by?: number | null;
  attendance_actions_available?: boolean;
};

function normalizeOperationsDashboardTripSummary(
  trip: OperationsDashboardTripApiPayload,
): OperationsDashboardTripSummary {
  const launchReadiness = normalizeDashboardLaunchReadiness(trip);
  return {
    id: trip.id ?? 0,
    title: trip.title ?? "Trip setup",
    startDate: trip.start_date ?? "",
    endDate: trip.end_date ?? "",
    capacity: trip.capacity ?? 0,
    publicationState: trip.publication_state ?? "draft",
    bookingAvailability: launchReadiness.bookingAvailability,
    effectiveBookingAvailability: launchReadiness.effectiveBookingAvailability,
    availableSeats: launchReadiness.availableSeats,
    coreOperationalBookingCount: trip.core_operational_booking_count ?? 0,
    operationalMetrics: normalizeOperationalMetrics(trip.operational_metrics),
    launchReadiness,
  };
}

function normalizeOperationsDashboardAttentionItem(
  item: OperationsDashboardAttentionApiPayload,
): OperationsDashboardAttentionItem {
  return {
    id: item.id ?? `${item.trip_id ?? 0}-${item.kind ?? "launch_blocker"}`,
    kind: item.kind ?? "launch_blocker",
    tripId: item.trip_id ?? 0,
    tripTitle: item.trip_title ?? "Trip",
    count: item.count ?? 0,
    amountInr: item.amount_inr ?? 0,
    message: item.message ?? "Review this Trip.",
    tone: item.tone ?? "attention",
  };
}

function normalizeDashboardLaunchReadiness(
  trip: OperationsDashboardTripApiPayload,
): OperationsDashboardLaunchReadiness {
  const readiness = trip.launch_readiness;
  const paymentMethodReadiness = normalizePaymentMethodReadiness(readiness);
  const bookingAvailability =
    readiness?.booking_availability ?? trip.booking_availability ?? "closed";
  const effectiveBookingAvailability =
    readiness?.effective_booking_availability ??
    trip.effective_booking_availability ??
    "closed";

  return {
    ctaEnabled: readiness?.cta_enabled ?? readiness?.ready ?? false,
    ready: readiness?.ready ?? false,
    reasonCode: readiness?.reason_code ?? "booking_closed",
    requestedSeats: readiness?.requested_seats ?? 1,
    publicationReady: readiness?.publication_ready ?? false,
    bookingAvailabilityOpen: readiness?.booking_availability_open ?? false,
    paymentMethodReadinessReady: paymentMethodReadiness.ready,
    paymentMethodReadinessStatusLabel: paymentMethodReadiness.statusLabel,
    readyPaymentMethodCount: paymentMethodReadiness.readyMethodCount,
    readyPaymentMethodIds: paymentMethodReadiness.readyMethodIds,
    paymentMethods: paymentMethodReadiness.methods,
    providerPaymentMethod: paymentMethodReadiness.providerPaymentMethod,
    manualPaymentMethod: paymentMethodReadiness.manualPaymentMethod,
    onlinePaymentReadinessReady:
      readiness?.online_payment_readiness_ready ??
      readiness?.provider_payment_setup_complete ??
      false,
    onlinePaymentReadinessStatusLabel:
      readiness?.online_payment_readiness_status_label ??
      (readiness?.provider_payment_setup_complete ? "Ready" : "Blocked"),
    onlinePaymentReadinessMessage:
      readiness?.online_payment_readiness_message ??
      (readiness?.provider_payment_setup_complete
        ? "Online Payment Readiness is ready for public booking."
        : "Online Payment Readiness is blocked."),
    providerPaymentSetupComplete:
      readiness?.provider_payment_setup_complete ?? false,
    capacityAvailable: readiness?.capacity_available ?? false,
    availableSeats: readiness?.available_seats ?? trip.available_seats ?? 0,
    activeSeatHolds: readiness?.active_seat_holds ?? 0,
    bookableSeats:
      readiness?.bookable_seats ??
      readiness?.available_seats ??
      trip.available_seats ??
      0,
    bookingAvailability,
    bookingAvailabilityLabel:
      readiness?.booking_availability_label ?? titleCase(bookingAvailability),
    effectiveBookingAvailability,
    effectiveBookingAvailabilityLabel:
      readiness?.effective_booking_availability_label ??
      titleCase(effectiveBookingAvailability),
    availabilityBand: readiness?.availability_band ?? "sold_out",
    availabilityBandLabel: readiness?.availability_band_label ?? "Sold out",
    ctaState:
      readiness?.cta_state ??
      (readiness?.cta_enabled || readiness?.ready ? "enabled" : "disabled"),
    message: readiness?.message ?? "Booking is not available.",
  };
}

function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function normalizeOperationalMetrics(
  payload?: OperationsMetricsApiPayload,
): OperationalMetrics {
  return {
    unpaidBookings: payload?.unpaid_bookings ?? 0,
    overdueAmountInr: payload?.overdue_amount_inr ?? 0,
    pendingManualPayments: payload?.pending_manual_payments ?? 0,
    pendingManualPaymentsSupported:
      payload?.pending_manual_payments_supported ?? false,
    missingRequirements: payload?.missing_requirements ?? 0,
    missingRequirementsSupported:
      payload?.missing_requirements_supported ?? false,
    availableSeats: payload?.available_seats ?? 0,
    reservedTravelers: payload?.reserved_travelers ?? 0,
    coreOperationalBookingCount: payload?.core_operational_booking_count ?? 0,
    bookingStateCounts: payload?.booking_state_counts ?? {},
  };
}

function normalizeOperationsBooking(
  payload: OperationsBookingApiPayload,
): OperationsBooking {
  return {
    id: payload.id ?? 0,
    bookingState: payload.booking_state ?? "draft",
    bookingStateLabel: payload.booking_state_label ?? "Draft",
    bookingContactName: payload.booking_contact_name ?? "Booking Contact",
    bookingContactPhone: payload.booking_contact_phone ?? "",
    bookingContactEmail: payload.booking_contact_email ?? "",
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
    },
    confirmationRequirements: {
      ready: payload.confirmation_requirements?.ready ?? false,
      unmetCount: payload.confirmation_requirements?.unmet_count ?? 0,
      unmet:
        payload.confirmation_requirements?.unmet?.map((requirement) => ({
          code: requirement.code ?? "requirement",
          label: requirement.label ?? "Confirmation Requirement",
          scope: requirement.scope ?? "booking",
          travelerSlotId: requirement.traveler_slot_id ?? null,
          travelerSlotPosition: requirement.traveler_slot_position ?? null,
        })) ?? [],
    },
    manualPayments:
      payload.manual_payments?.map(normalizeOperationsManualPayment) ?? [],
    travelerSlots:
      payload.traveler_slots?.map(normalizeOperationsTravelerSlot) ?? [],
    attendanceSummary: {
      notMarked: payload.attendance_summary?.not_marked ?? 0,
      checkedIn: payload.attendance_summary?.checked_in ?? 0,
      noShow: payload.attendance_summary?.no_show ?? 0,
    },
    draftExpiresAt: payload.draft_expires_at ?? "",
    createdAt: payload.created_at ?? "",
    updatedAt: payload.updated_at ?? "",
  };
}

function normalizeOperationsTravelerSlot(
  payload: OperationsTravelerSlotApiPayload,
): OperationsTravelerSlot {
  return {
    id: payload.id ?? 0,
    position: payload.position ?? 0,
    packageName: payload.package_name ?? "Package",
    travelerFullName: payload.traveler_full_name ?? "",
    travelerPhone: payload.traveler_phone ?? "",
    travelerEmail: payload.traveler_email ?? "",
    isTraveler: payload.is_traveler ?? false,
    attendanceState: payload.attendance_state ?? "not_marked",
    attendanceStateLabel: payload.attendance_state_label ?? "Not marked",
    attendanceMarkedAt: payload.attendance_marked_at ?? null,
    attendanceMarkedBy: payload.attendance_marked_by ?? null,
    attendanceActionsAvailable: payload.attendance_actions_available ?? false,
  };
}

function normalizeOperationsManualPayment(
  payload: OperationsManualPaymentApiPayload,
): OperationsManualPayment {
  return {
    id: payload.id ?? 0,
    source: payload.source ?? "traveler_submitted",
    sourceLabel: payload.source_label ?? "Traveler-submitted",
    status: payload.status ?? "submitted",
    statusLabel: payload.status_label ?? "Submitted",
    amountInr: payload.amount_inr ?? 0,
    paymentReference: payload.payment_reference ?? "",
    originalFilename: payload.original_filename ?? "",
    hasPaymentProof: payload.has_payment_proof ?? false,
    isSensitivePaymentInformation:
      payload.is_sensitive_payment_information ?? false,
    excludeFromDefaultExports: payload.exclude_from_default_exports ?? false,
    submittedAt: payload.submitted_at ?? "",
  };
}

export async function updateTripLaunchState({
  organizerId,
  tripId,
  publicationState,
  bookingAvailability,
  manualPaymentAvailability,
  publishLockAcknowledged,
}: {
  organizerId: number;
  tripId: number;
  publicationState?: "draft" | "published" | "archived";
  bookingAvailability?: "closed" | "open";
  manualPaymentAvailability?: "closed" | "open";
  publishLockAcknowledged?: boolean;
}): Promise<{ publicUrlPath: string | null }> {
  const result = await authenticatedServerJsonRequest<{
    public_url_path?: string;
  }>(
    `/api/organizers/${organizerId}/trips/${tripId}/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        ...(publicationState ? { publication_state: publicationState } : {}),
        ...(publishLockAcknowledged === undefined
          ? {}
          : { publish_lock_acknowledged: publishLockAcknowledged }),
        ...(bookingAvailability
          ? { booking_availability: bookingAvailability }
          : {}),
        ...(manualPaymentAvailability
          ? { manual_payment_availability: manualPaymentAvailability }
          : {}),
      },
    },
  );

  if (!result.response.ok) {
    throw new Error(launchStateError(result.errorPayload));
  }

  return {
    publicUrlPath:
      typeof result.data?.public_url_path === "string"
        ? result.data.public_url_path
        : null,
  };
}

function launchStateError(payload: unknown): string {
  return extractDrfErrorMessage(payload) ?? "Trip Launch update failed.";
}
