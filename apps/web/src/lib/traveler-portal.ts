import { multipartFormRequest, publicJsonRequest } from "./drf-request.ts";
import {
  normalizeOrganizerIdentity,
  type OrganizerIdentity,
  type OrganizerIdentityApiPayload
} from "./organizer-identity.ts";

export type TravelerPortal = {
  ok: true;
  accessScope: "booking" | "traveler";
  accessExpiresAt: string;
  organizerIdentity: OrganizerIdentity;
  trip: {
    id: number;
    title: string;
    startDate: string;
    endDate: string;
  };
  booking: {
    id: number;
    bookingState: string;
    bookingStateLabel: string;
    bookingTotalInr: number;
    bookingReservationAmountInr: number;
  };
  balancePayment: BalancePaymentAvailability;
  bookingContact: {
    name: string;
    phone: string;
    email: string;
  };
  manualPayments: TravelerManualPayment[];
  travelerSlots: TravelerIdentity[];
};

export type TravelerManualPayment = {
  id: number;
  source: string;
  sourceLabel: string;
  status: "submitted" | "approved" | "rejected";
  statusLabel: string;
  amountInr: number;
  paymentReference: string;
  hasPaymentProof: boolean;
  isSensitivePaymentInformation: boolean;
  excludeFromDefaultExports: boolean;
  submittedAt: string;
};

export type BalancePaymentAvailability = {
  available: boolean;
  blockerCode:
    | "ready"
    | "booking_access_required"
    | "booking_not_reserved"
    | "booking_cancelled"
    | "fully_paid"
    | "online_payment_readiness_missing";
  message: string;
  amountInr: number;
  currency: string;
  paymentPurpose: "balance";
  paymentLinkPath: string;
};

export type BalanceCheckout = {
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

export type BalanceCheckoutResult =
  | {
      ok: true;
      bookingId: number;
      paymentAttemptId: number;
      provider: string;
      purpose: string;
      status: string;
      amountInr: number;
      providerAttemptReference: string;
      checkout: BalanceCheckout;
    }
  | {
      ok: false;
      message: string;
    };

export type TravelerIdentity = {
  id: number;
  position: number;
  packageName: string;
  travelerFullName: string;
  travelerPhone: string;
  travelerEmail: string;
  isTraveler: boolean;
};

export type TravelerPortalUnavailable = {
  ok: false;
  status: "invalid" | "unreachable";
};

export type UpdateTravelerIdentityResult =
  | {
      ok: true;
    }
  | {
      ok: false;
      message: string;
    };

export type SubmitManualPaymentResult =
  | {
      ok: true;
    }
  | {
      ok: false;
      message: string;
    };

export async function getTravelerPortal(
  token: string
): Promise<TravelerPortal | TravelerPortalUnavailable> {
  try {
    const result = await publicJsonRequest<TravelerPortalApiPayload>(
      `/api/portal/${token}/`
    );

    if (!result.response.ok || !result.data) {
      return { ok: false, status: "invalid" };
    }

    return normalizeTravelerPortal(result.data);
  } catch {
    return { ok: false, status: "unreachable" };
  }
}

export async function updateTravelerIdentity(input: {
  token: string;
  travelerSlotId: number;
  travelerFullName: string;
  travelerPhone: string;
  travelerEmail?: string;
}): Promise<UpdateTravelerIdentityResult> {
  try {
    const result = await publicJsonRequest(
      `/api/portal/${input.token}/traveler-slots/${input.travelerSlotId}/identity/`,
      {
        method: "PATCH",
        body: {
          traveler_full_name: input.travelerFullName,
          traveler_phone: input.travelerPhone,
          traveler_email: input.travelerEmail ?? ""
        }
      }
    );

    if (!result.response.ok) {
      return {
        ok: false,
        message: "Traveler Identity Details need full name and phone number."
      };
    }

    return { ok: true };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach the Traveler Portal. Please try again."
    };
  }
}

export async function submitTravelerManualPayment(input: {
  token: string;
  amountInr: number;
  paymentReference?: string;
  note?: string;
  paymentProof: File;
}): Promise<SubmitManualPaymentResult> {
  const formData = new FormData();
  formData.append("amount_inr", String(input.amountInr));
  formData.append("payment_reference", input.paymentReference ?? "");
  formData.append("note", input.note ?? "");
  formData.append("payment_proof", input.paymentProof);

  try {
    const result = await multipartFormRequest(`/api/portal/${input.token}/manual-payments/`, {
      method: "POST",
      formData
    });

    if (!result.response.ok) {
      return {
        ok: false,
        message: "Manual Payment needs an amount and Payment Proof."
      };
    }

    return { ok: true };
  } catch {
    return {
      ok: false,
      message: "TripOS could not upload Payment Proof. Please try again."
    };
  }
}

export async function startBalancePaymentCheckout(
  token: string
): Promise<BalanceCheckoutResult> {
  try {
    const result = await publicJsonRequest<PaymentAttemptApiPayload>(
      `/api/portal/${token}/balance-payment-attempts/`,
      {
        method: "POST"
      }
    );

    if (!result.response.ok || !result.data?.checkout) {
      return {
        ok: false,
        message: "Balance checkout could not be started for this Booking."
      };
    }

    const normalized = normalizeBalanceCheckoutAttempt(result.data);
    return {
      ok: true,
      bookingId: normalized.bookingId,
      paymentAttemptId: normalized.paymentAttemptId,
      provider: normalized.provider,
      purpose: normalized.purpose,
      status: normalized.status,
      amountInr: normalized.amountInr,
      providerAttemptReference: normalized.providerAttemptReference,
      checkout: normalized.checkout
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach balance checkout. Please try again."
    };
  }
}

type TravelerPortalApiPayload = {
  access_scope?: "booking" | "traveler";
  access_expires_at?: string;
  organizer_identity?: OrganizerIdentityApiPayload;
  trip?: {
    id?: number;
    title?: string;
    start_date?: string;
    end_date?: string;
  };
  booking?: {
    id?: number;
    booking_state?: string;
    booking_state_label?: string;
    booking_total_inr?: number;
    booking_reservation_amount_inr?: number;
  };
  balance_payment?: BalancePaymentApiPayload;
  booking_contact?: {
    name?: string;
    phone?: string;
    email?: string;
  };
  manual_payments?: TravelerManualPaymentApiPayload[];
  traveler_slots?: TravelerIdentityApiPayload[];
};

type BalancePaymentApiPayload = {
  available?: boolean;
  blocker_code?: BalancePaymentAvailability["blockerCode"];
  message?: string;
  amount_inr?: number;
  currency?: string;
  payment_purpose?: "balance";
  payment_link_path?: string;
};

type TravelerManualPaymentApiPayload = {
  id?: number;
  source?: string;
  source_label?: string;
  status?: "submitted" | "approved" | "rejected";
  status_label?: string;
  amount_inr?: number;
  payment_reference?: string;
  has_payment_proof?: boolean;
  is_sensitive_payment_information?: boolean;
  exclude_from_default_exports?: boolean;
  submitted_at?: string;
};

type TravelerIdentityApiPayload = {
  id?: number;
  position?: number;
  package_name?: string;
  traveler_full_name?: string;
  traveler_phone?: string;
  traveler_email?: string;
  is_traveler?: boolean;
};

type PaymentAttemptApiPayload = {
  id?: number;
  booking?: number;
  provider?: string;
  purpose?: string;
  status?: string;
  amount_inr?: number;
  provider_attempt_reference?: string;
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

function normalizeTravelerPortal(payload: TravelerPortalApiPayload): TravelerPortal {
  return {
    ok: true,
    accessScope: payload.access_scope ?? "traveler",
    accessExpiresAt: payload.access_expires_at ?? "",
    organizerIdentity: normalizeOrganizerIdentity(
      payload.organizer_identity,
      "TripOS Organizer",
    ),
    trip: {
      id: payload.trip?.id ?? 0,
      title: payload.trip?.title ?? "Trip",
      startDate: payload.trip?.start_date ?? "",
      endDate: payload.trip?.end_date ?? ""
    },
    booking: {
      id: payload.booking?.id ?? 0,
      bookingState: payload.booking?.booking_state ?? "draft",
      bookingStateLabel: payload.booking?.booking_state_label ?? "Draft",
      bookingTotalInr: payload.booking?.booking_total_inr ?? 0,
      bookingReservationAmountInr: payload.booking?.booking_reservation_amount_inr ?? 0
    },
    balancePayment: normalizeBalancePayment(payload.balance_payment),
    bookingContact: {
      name: payload.booking_contact?.name ?? "",
      phone: payload.booking_contact?.phone ?? "",
      email: payload.booking_contact?.email ?? ""
    },
    manualPayments: (payload.manual_payments ?? []).map(normalizeTravelerManualPayment),
    travelerSlots: (payload.traveler_slots ?? []).map(normalizeTravelerIdentity)
  };
}

function normalizeBalancePayment(
  payload: BalancePaymentApiPayload | undefined
): BalancePaymentAvailability {
  return {
    available: payload?.available ?? false,
    blockerCode: payload?.blocker_code ?? "booking_access_required",
    message: payload?.message ?? "Balance Payment Links require Booking-Level Access.",
    amountInr: payload?.amount_inr ?? 0,
    currency: payload?.currency ?? "INR",
    paymentPurpose: payload?.payment_purpose ?? "balance",
    paymentLinkPath: payload?.payment_link_path ?? ""
  };
}

function normalizeBalanceCheckoutAttempt(payload: PaymentAttemptApiPayload) {
  return {
    bookingId: payload.booking ?? 0,
    paymentAttemptId: payload.id ?? 0,
    provider: payload.provider ?? "razorpay",
    purpose: payload.purpose ?? "balance",
    status: payload.status ?? "pending",
    amountInr: payload.amount_inr ?? 0,
    providerAttemptReference: payload.provider_attempt_reference ?? "",
    checkout: {
      provider: payload.checkout?.provider ?? payload.provider ?? "razorpay",
      providerOrderReference:
        payload.checkout?.provider_order_reference ?? payload.provider_attempt_reference ?? "",
      amountInr: payload.checkout?.amount_inr ?? payload.amount_inr ?? 0,
      amountMinor:
        payload.checkout?.amount_minor ??
        (payload.checkout?.amount_inr ?? payload.amount_inr ?? 0) * 100,
      currency: payload.checkout?.currency ?? "INR",
      paymentAttempt: payload.checkout?.payment_attempt ?? payload.id ?? 0,
      booking: payload.checkout?.booking ?? payload.booking ?? 0,
      paymentPurpose: payload.checkout?.payment_purpose ?? payload.purpose ?? "balance",
      providerPayload: payload.checkout?.provider_payload ?? {}
    }
  };
}

function normalizeTravelerManualPayment(
  payload: TravelerManualPaymentApiPayload
): TravelerManualPayment {
  return {
    id: payload.id ?? 0,
    source: payload.source ?? "traveler_submitted",
    sourceLabel: payload.source_label ?? "Traveler-submitted",
    status: payload.status ?? "submitted",
    statusLabel: payload.status_label ?? "Submitted",
    amountInr: payload.amount_inr ?? 0,
    paymentReference: payload.payment_reference ?? "",
    hasPaymentProof: payload.has_payment_proof ?? false,
    isSensitivePaymentInformation: payload.is_sensitive_payment_information ?? false,
    excludeFromDefaultExports: payload.exclude_from_default_exports ?? false,
    submittedAt: payload.submitted_at ?? ""
  };
}

function normalizeTravelerIdentity(payload: TravelerIdentityApiPayload): TravelerIdentity {
  return {
    id: payload.id ?? 0,
    position: payload.position ?? 0,
    packageName: payload.package_name ?? "Package",
    travelerFullName: payload.traveler_full_name ?? "",
    travelerPhone: payload.traveler_phone ?? "",
    travelerEmail: payload.traveler_email ?? "",
    isTraveler: payload.is_traveler ?? false
  };
}
