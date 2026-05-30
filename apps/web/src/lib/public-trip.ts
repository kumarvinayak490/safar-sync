import {
  drfApiUrl,
  multipartFormRequest,
  publicJsonRequest,
} from "./drf-request.ts";
import {
  normalizeOrganizerIdentity,
  type OrganizerIdentity,
  type OrganizerIdentityApiPayload,
} from "./organizer-identity.ts";
import {
  normalizePaymentMethodReadiness,
  type PaymentMethodReadiness,
  type PaymentMethodReadinessApiPayload,
} from "./payment-method-readiness.ts";
import {
  normalizeTripRichText,
  type TripRichTextDocument,
} from "./trip-rich-text.ts";
import {
  normalizeTripItineraryDays,
  normalizeTripMediaItems,
  type TripItineraryDay,
  type TripMediaItem,
} from "./trip-profile.ts";

export type AvailabilityBand = "available" | "few_seats_left" | "sold_out";

export type PublicBookingGateDecision = {
  ctaEnabled: boolean;
  ready: boolean;
  reasonCode:
    | "ready"
    | "publication_not_published"
    | "booking_closed"
    | "payment_method_readiness_missing"
    | "online_payment_readiness_missing"
    | "provider_payment_setup_incomplete"
    | "sold_out"
    | "insufficient_capacity";
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
  providerCheckoutVisible: boolean;
  primaryPaymentActionLabel: string;
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
  availabilityBand: AvailabilityBand;
  availabilityBandLabel: string;
  ctaState: "enabled" | "disabled";
  message: string;
};

export type PublicManualPaymentInstructions = {
  ready: boolean;
  message: string;
  paymentQrUrl: string;
  upiId: string;
  accountName: string;
  bankTransferDetails: string;
};

export type PublicTrip = {
  ok: true;
  id: number;
  title: string;
  slug: string;
  startDate: string;
  endDate: string;
  descriptionRichText: TripRichTextDocument;
  confirmationRequirementsNote: string;
  itinerary: string;
  itineraryDays: TripItineraryDay[];
  mediaItems: TripMediaItem[];
  publicationState: string;
  publicationStateLabel: string;
  bookingAvailability: string;
  bookingAvailabilityLabel: string;
  effectiveBookingAvailability: string;
  publicUrlPath: string;
  organizerIdentity: OrganizerIdentity;
  packages: Array<{
    id: number;
    name: string;
    description: string;
    priceInr: number;
    reservationAmountInr: number;
    position: number;
  }>;
  paymentSchedule: {
    reservationMilestone: {
      type: string;
      due: string;
      amountSource: string;
    };
    balanceDueDaysBeforeStart: number | null;
    balanceDueDate: string | null;
    balanceReminderLeadDays: number;
    hasBalanceMilestone: boolean;
  };
  availabilityBand: AvailabilityBand;
  availabilityBandLabel: string;
  publicBookingGate: PublicBookingGateDecision;
  manualPaymentInstructions: PublicManualPaymentInstructions | null;
  updatedAt: string;
};

export type PublicTripUnavailable = {
  ok: false;
  status: "not_found" | "unreachable";
};

export type CreateDraftBookingInput = {
  organizerSlug: string;
  tripSlug: string;
  bookingContactName: string;
  bookingContactPhone: string;
  bookingContactEmail?: string;
  travelerCount: number;
  packageId: number;
};

export type CreateDraftBookingResult =
  | {
      ok: true;
      bookingId: number;
      draftExpiresAt: string;
    }
  | {
      ok: false;
      message: string;
    };

export type ReservationCheckout = {
  provider: string;
  providerOrderReference: string;
  amountInr: number;
  amountMinor: number;
  currency: string;
  paymentAttempt: number;
  booking: number;
  paymentPurpose: string;
  providerPayload: Record<string, unknown>;
};

export type ReservationCheckoutResult =
  | {
      ok: true;
      bookingId: number;
      paymentAttemptId: number;
      provider: string;
      purpose: string;
      status: string;
      amountInr: number;
      providerAttemptReference: string;
      checkout: ReservationCheckout;
    }
  | {
      ok: false;
      message: string;
    };

export type CheckoutSuccessResult =
  | {
      ok: true;
      paymentAttemptId: number;
      status: string;
      checkoutSucceededAt: string;
    }
  | {
      ok: false;
      message: string;
    };

export type CheckoutSuccessInput = {
  razorpayPaymentId: string;
  razorpayOrderId: string;
  razorpaySignature: string;
};

export type SubmitPublicManualPaymentProofInput = CreateDraftBookingInput & {
  paymentProof: File;
  paymentReference?: string;
  note?: string;
};

export type SubmitPublicManualPaymentProofResult =
  | {
      ok: true;
      bookingId: number;
      manualPaymentId: number;
      status: string;
      amountInr: number;
      paymentReference: string;
    }
  | {
      ok: false;
      message: string;
    };

export async function getPublicTrip(
  organizerSlug: string,
  tripSlug: string,
): Promise<PublicTrip | PublicTripUnavailable> {
  try {
    const result = await publicJsonRequest<PublicTripApiPayload>(
      `/api/public/trips/${organizerSlug}/${tripSlug}/`,
    );

    if (result.response.status === 404) {
      return { ok: false, status: "not_found" };
    }

    if (!result.response.ok || !result.data) {
      return { ok: false, status: "unreachable" };
    }

    return normalizePublicTrip(result.data);
  } catch {
    return { ok: false, status: "unreachable" };
  }
}

export async function createPublicDraftBooking(
  input: CreateDraftBookingInput,
): Promise<CreateDraftBookingResult> {
  try {
    const result = await publicJsonRequest<{
      id?: number;
      draft_expires_at?: string;
    }>(
      `/api/public/trips/${input.organizerSlug}/${input.tripSlug}/draft-bookings/`,
      {
        method: "POST",
        body: {
          booking_contact_name: input.bookingContactName,
          booking_contact_phone: input.bookingContactPhone,
          booking_contact_email: input.bookingContactEmail ?? "",
          traveler_count: input.travelerCount,
          package: input.packageId,
        },
      },
    );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          "Draft Booking could not be created. Check the contact details and packages.",
      };
    }

    return {
      ok: true,
      bookingId: result.data.id ?? 0,
      draftExpiresAt: result.data.draft_expires_at ?? "",
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach booking intake. Please try again.",
    };
  }
}

export async function startReservationCheckout(
  bookingId: number,
): Promise<ReservationCheckoutResult> {
  try {
    const result = await publicJsonRequest<PaymentAttemptApiPayload>(
      `/api/public/bookings/${bookingId}/payment-attempts/`,
      {
        method: "POST",
      },
    );

    if (!result.response.ok || !result.data?.checkout) {
      return {
        ok: false,
        message:
          "Reservation checkout could not be started for this Draft Booking.",
      };
    }

    const normalized = normalizeReservationCheckoutAttempt(result.data);
    return {
      ok: true,
      bookingId: normalized.bookingId,
      paymentAttemptId: normalized.paymentAttemptId,
      provider: normalized.provider,
      purpose: normalized.purpose,
      status: normalized.status,
      amountInr: normalized.amountInr,
      providerAttemptReference: normalized.providerAttemptReference,
      checkout: normalized.checkout,
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach reservation checkout. Please try again.",
    };
  }
}

export async function recordCheckoutSuccess(
  paymentAttemptId: number,
  input: CheckoutSuccessInput,
): Promise<CheckoutSuccessResult> {
  try {
    const result = await publicJsonRequest<PaymentAttemptApiPayload>(
      `/api/public/payment-attempts/${paymentAttemptId}/checkout-success/`,
      {
        method: "POST",
        body: {
          razorpay_payment_id: input.razorpayPaymentId,
          razorpay_order_id: input.razorpayOrderId,
          razorpay_signature: input.razorpaySignature,
        },
      },
    );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message: "Checkout success could not be recorded.",
      };
    }

    return {
      ok: true,
      paymentAttemptId: result.data.id ?? paymentAttemptId,
      status: result.data.status ?? "confirming",
      checkoutSucceededAt: result.data.checkout_succeeded_at ?? "",
    };
  } catch {
    return {
      ok: false,
      message:
        "TripOS could not reach checkout confirmation. Please try again.",
    };
  }
}

export async function submitPublicManualPaymentProof(
  input: SubmitPublicManualPaymentProofInput,
): Promise<SubmitPublicManualPaymentProofResult> {
  const formData = new FormData();
  formData.append("booking_contact_name", input.bookingContactName);
  formData.append("booking_contact_phone", input.bookingContactPhone);
  formData.append("booking_contact_email", input.bookingContactEmail ?? "");
  formData.append("traveler_count", String(input.travelerCount));
  formData.append("package", String(input.packageId));
  formData.append("payment_reference", input.paymentReference ?? "");
  formData.append("note", input.note ?? "");
  formData.append("payment_proof", input.paymentProof);

  try {
    const result = await multipartFormRequest<ManualPaymentApiPayload>(
      `/api/public/trips/${input.organizerSlug}/${input.tripSlug}/manual-payments/`,
      {
        method: "POST",
        formData,
      },
    );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          result.errorMessage ??
          "Payment Proof could not be submitted. Check the file and booking details.",
      };
    }

    return {
      ok: true,
      bookingId: result.data.booking ?? 0,
      manualPaymentId: result.data.id ?? 0,
      status: result.data.status ?? "submitted",
      amountInr: result.data.amount_inr ?? 0,
      paymentReference: result.data.payment_reference ?? "",
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not upload Payment Proof. Please try again.",
    };
  }
}

type PublicTripApiPayload = {
  id?: number;
  title?: string;
  slug?: string;
  start_date?: string;
  end_date?: string;
  confirmation_requirements_note?: string;
  description_rich_text?: unknown;
  itinerary?: string;
  itinerary_days?: unknown;
  media_items?: unknown;
  publication_state?: string;
  publication_state_label?: string;
  booking_availability?: string;
  booking_availability_label?: string;
  effective_booking_availability?: string;
  public_url_path?: string;
  organizer_identity?: OrganizerIdentityApiPayload;
  packages?: Array<{
    id?: number;
    name?: string;
    description?: string;
    price_inr?: number;
    reservation_amount_inr?: number;
    position?: number;
  }>;
  payment_schedule?: {
    reservation_milestone?: {
      type?: string;
      due?: string;
      amount_source?: string;
    };
    balance_due_days_before_start?: number | null;
    balance_due_date?: string | null;
    balance_reminder_lead_days?: number;
    has_balance_milestone?: boolean;
  };
  availability_band?: AvailabilityBand;
  availability_band_label?: string;
  public_booking_gate?: PaymentMethodReadinessApiPayload & {
    cta_enabled?: boolean;
    ready?: boolean;
    reason_code?: PublicBookingGateDecision["reasonCode"];
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
    availability_band?: AvailabilityBand;
    availability_band_label?: string;
    cta_state?: "enabled" | "disabled";
    message?: string;
  };
  manual_payment_instructions?: {
    ready?: boolean;
    message?: string;
    payment_qr_url?: string;
    upi_id?: string;
    account_name?: string;
    bank_transfer_details?: string;
  } | null;
  updated_at?: string;
};

type PaymentAttemptApiPayload = {
  id?: number;
  booking?: number;
  provider?: string;
  purpose?: string;
  status?: string;
  amount_inr?: number;
  provider_attempt_reference?: string;
  checkout_succeeded_at?: string;
  checkout?: {
    provider?: string;
    provider_order_reference?: string;
    amount_inr?: number;
    amount_minor?: number;
    currency?: string;
    payment_attempt?: number;
    booking?: number;
    payment_purpose?: string;
    provider_payload?: Record<string, unknown>;
  };
};

type ManualPaymentApiPayload = {
  id?: number;
  booking?: number;
  status?: string;
  amount_inr?: number;
  payment_reference?: string;
};

export function normalizePublicTrip(payload: PublicTripApiPayload): PublicTrip {
  const publicBookingGate = normalizePublicBookingGate(payload);

  return {
    ok: true,
    id: payload.id ?? 0,
    title: payload.title ?? "Trip",
    slug: payload.slug ?? "",
    startDate: payload.start_date ?? "",
    endDate: payload.end_date ?? "",
    descriptionRichText: normalizeTripRichText(payload.description_rich_text),
    confirmationRequirementsNote: payload.confirmation_requirements_note ?? "",
    itinerary: payload.itinerary ?? "",
    itineraryDays: normalizeTripItineraryDays(payload.itinerary_days),
    mediaItems: normalizeTripMediaItems(payload.media_items),
    publicationState: payload.publication_state ?? "published",
    publicationStateLabel: payload.publication_state_label ?? "Published",
    bookingAvailability: publicBookingGate.bookingAvailability,
    bookingAvailabilityLabel: publicBookingGate.bookingAvailabilityLabel,
    effectiveBookingAvailability:
      publicBookingGate.effectiveBookingAvailability,
    publicUrlPath: payload.public_url_path ?? "",
    organizerIdentity: normalizeOrganizerIdentity(payload.organizer_identity),
    packages:
      payload.packages?.map((tripPackage) => ({
        id: tripPackage.id ?? 0,
        name: tripPackage.name ?? "Package",
        description: tripPackage.description ?? "",
        priceInr: tripPackage.price_inr ?? 0,
        reservationAmountInr: tripPackage.reservation_amount_inr ?? 0,
        position: tripPackage.position ?? 1,
      })) ?? [],
    paymentSchedule: {
      reservationMilestone: {
        type:
          payload.payment_schedule?.reservation_milestone?.type ??
          "reservation",
        due:
          payload.payment_schedule?.reservation_milestone?.due ?? "immediate",
        amountSource:
          payload.payment_schedule?.reservation_milestone?.amount_source ??
          "package_reservation_amounts",
      },
      balanceDueDaysBeforeStart:
        payload.payment_schedule?.balance_due_days_before_start ?? null,
      balanceDueDate: payload.payment_schedule?.balance_due_date ?? null,
      balanceReminderLeadDays:
        payload.payment_schedule?.balance_reminder_lead_days ?? 3,
      hasBalanceMilestone:
        payload.payment_schedule?.has_balance_milestone ?? false,
    },
    availabilityBand: publicBookingGate.availabilityBand,
    availabilityBandLabel: publicBookingGate.availabilityBandLabel,
    publicBookingGate,
    manualPaymentInstructions:
      normalizePublicManualPaymentInstructions(payload),
    updatedAt: payload.updated_at ?? "",
  };
}

function normalizeReservationCheckoutAttempt(
  payload: PaymentAttemptApiPayload,
) {
  const checkout = payload.checkout ?? {};
  const providerPayload = checkout.provider_payload ?? {};
  return {
    bookingId: payload.booking ?? checkout.booking ?? 0,
    paymentAttemptId: payload.id ?? checkout.payment_attempt ?? 0,
    provider: payload.provider ?? checkout.provider ?? "razorpay",
    purpose: payload.purpose ?? checkout.payment_purpose ?? "reservation",
    status: payload.status ?? "pending",
    amountInr: payload.amount_inr ?? checkout.amount_inr ?? 0,
    providerAttemptReference:
      payload.provider_attempt_reference ??
      checkout.provider_order_reference ??
      "",
    checkout: {
      provider: checkout.provider ?? payload.provider ?? "razorpay",
      providerOrderReference:
        checkout.provider_order_reference ??
        payload.provider_attempt_reference ??
        "",
      amountInr: checkout.amount_inr ?? payload.amount_inr ?? 0,
      amountMinor: checkout.amount_minor ?? (payload.amount_inr ?? 0) * 100,
      currency: checkout.currency ?? "INR",
      paymentAttempt: checkout.payment_attempt ?? payload.id ?? 0,
      booking: checkout.booking ?? payload.booking ?? 0,
      paymentPurpose:
        checkout.payment_purpose ?? payload.purpose ?? "reservation",
      providerPayload,
    },
  };
}

function normalizePublicBookingGate(
  payload: PublicTripApiPayload,
): PublicBookingGateDecision {
  const gate = payload.public_booking_gate;
  const paymentMethodReadiness = normalizePaymentMethodReadiness(gate);
  const providerCheckoutVisible =
    paymentMethodReadiness.providerPaymentMethod.ready &&
    (gate?.online_payment_readiness_ready ?? false);
  const manualPaymentVisible =
    paymentMethodReadiness.manualPaymentMethod.ready &&
    !!payload.manual_payment_instructions?.ready;
  const paymentActionLabel = providerCheckoutVisible
    ? paymentMethodReadiness.providerPaymentMethod.actionLabel
    : manualPaymentVisible
      ? paymentMethodReadiness.manualPaymentMethod.actionLabel
      : "";
  const primaryPaymentActionLabel = paymentActionLabel || "Start booking";
  const effectiveBookingAvailability =
    gate?.effective_booking_availability ??
    payload.effective_booking_availability ??
    "closed";
  const availabilityBand =
    gate?.availability_band ?? payload.availability_band ?? "sold_out";
  const bookingAvailability =
    gate?.booking_availability ?? payload.booking_availability ?? "closed";

  return {
    ctaEnabled: gate?.cta_enabled ?? false,
    ready: gate?.ready ?? false,
    reasonCode: gate?.reason_code ?? "booking_closed",
    requestedSeats: gate?.requested_seats ?? 1,
    publicationReady: gate?.publication_ready ?? false,
    bookingAvailabilityOpen: gate?.booking_availability_open ?? false,
    paymentMethodReadinessReady: paymentMethodReadiness.ready,
    paymentMethodReadinessStatusLabel: paymentMethodReadiness.statusLabel,
    readyPaymentMethodCount: paymentMethodReadiness.readyMethodCount,
    readyPaymentMethodIds: paymentMethodReadiness.readyMethodIds,
    paymentMethods: paymentMethodReadiness.methods,
    providerPaymentMethod: paymentMethodReadiness.providerPaymentMethod,
    manualPaymentMethod: paymentMethodReadiness.manualPaymentMethod,
    providerCheckoutVisible,
    primaryPaymentActionLabel,
    onlinePaymentReadinessReady: providerCheckoutVisible,
    onlinePaymentReadinessStatusLabel:
      gate?.online_payment_readiness_status_label ??
      (gate?.provider_payment_setup_complete ? "Ready" : "Blocked"),
    onlinePaymentReadinessMessage:
      gate?.online_payment_readiness_message ??
      (gate?.provider_payment_setup_complete
        ? "Online Payment Readiness is ready for public booking."
        : "Online Payment Readiness is blocked."),
    providerPaymentSetupComplete:
      gate?.provider_payment_setup_complete ?? false,
    capacityAvailable: gate?.capacity_available ?? false,
    availableSeats: gate?.available_seats ?? 0,
    activeSeatHolds: gate?.active_seat_holds ?? 0,
    bookableSeats: gate?.bookable_seats ?? gate?.available_seats ?? 0,
    bookingAvailability,
    bookingAvailabilityLabel:
      gate?.booking_availability_label ??
      payload.booking_availability_label ??
      titleCase(bookingAvailability),
    effectiveBookingAvailability,
    effectiveBookingAvailabilityLabel:
      gate?.effective_booking_availability_label ??
      titleCase(effectiveBookingAvailability),
    availabilityBand,
    availabilityBandLabel:
      gate?.availability_band_label ??
      payload.availability_band_label ??
      titleCase(availabilityBand),
    ctaState:
      gate?.cta_state ??
      (gate?.cta_enabled || gate?.ready ? "enabled" : "disabled"),
    message: gate?.message ?? "Booking is not available.",
  };
}

function normalizePublicManualPaymentInstructions(
  payload: PublicTripApiPayload,
): PublicManualPaymentInstructions | null {
  const instructions = payload.manual_payment_instructions;
  const manualMethodReady =
    payload.public_booking_gate?.manual_payment_method?.ready ??
    payload.public_booking_gate?.payment_methods?.some(
      (method) => method.id === "qr_manual_payments" && method.ready,
    ) ??
    false;

  if (!instructions?.ready || !manualMethodReady) {
    return null;
  }

  return {
    ready: true,
    message:
      instructions.message ??
      "Scan the Payment QR and submit Payment Proof for Organizer review.",
    paymentQrUrl: normalizePublicAssetUrl(instructions.payment_qr_url ?? ""),
    upiId: instructions.upi_id ?? "",
    accountName: instructions.account_name ?? "",
    bankTransferDetails: instructions.bank_transfer_details ?? "",
  };
}

function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function normalizePublicAssetUrl(url: string): string {
  if (!url || /^(https?:|data:|blob:)/i.test(url)) {
    return url;
  }
  return drfApiUrl(url.startsWith("/") ? url : `/${url}`);
}
