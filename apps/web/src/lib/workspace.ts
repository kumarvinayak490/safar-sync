import { authenticatedServerJsonRequest } from "./drf-request.ts";
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
  normalizeTripConfirmationRequirements,
  normalizeTripItineraryDays,
  normalizeTripMediaItems,
  normalizeTripPackages,
  normalizeTripPaymentSchedule,
  type TripConfirmationRequirements,
  type TripItineraryDay,
  type TripMediaItem,
  type TripProfilePackage,
  type TripPaymentSchedule,
} from "./trip-profile.ts";

export type LaunchReadinessDecision = {
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

export type TripProfilePublicationReadinessItem = {
  id: string;
  label: string;
  detail: string;
  sectionId: string;
  tone: "blocked" | "attention" | "clear" | "readonly";
  blocking: boolean;
};

export type TripProfilePublicationReadinessDecision = {
  blockers: TripProfilePublicationReadinessItem[];
  encouraged: TripProfilePublicationReadinessItem[];
  blockerCount: number;
  encouragedCount: number;
  publishEligible: boolean;
  lockAcknowledgementRequired: boolean;
};

export type WorkspaceTrip = {
  id: number;
  title: string;
  startDate: string;
  endDate: string;
  capacity: number;
  availableSeats: number;
  descriptionRichText?: TripRichTextDocument;
  itinerary?: string;
  itineraryDays?: TripItineraryDay[];
  mediaItems?: TripMediaItem[];
  packages?: TripProfilePackage[];
  paymentSchedule: TripPaymentSchedule;
  confirmationRequirements: TripConfirmationRequirements;
  publicationState: string;
  bookingAvailability: string;
  manualPaymentAvailability: string;
  effectiveBookingAvailability: string;
  publicUrlPath: string;
  launchReadiness: LaunchReadinessDecision;
  tripProfilePublicationReadiness: TripProfilePublicationReadinessDecision;
};

export async function getWorkspaceTrips(
  organizerId: number,
): Promise<WorkspaceTrip[]> {
  const result = await authenticatedServerJsonRequest<
    WorkspaceTripApiPayload[]
  >(`/api/organizers/${organizerId}/trips/`);

  if (!result.response.ok || !result.data) {
    return [];
  }

  return result.data.map(normalizeWorkspaceTrip);
}

export function normalizeWorkspaceTrip(
  trip: WorkspaceTripApiPayload,
): WorkspaceTrip {
  const launchReadiness = normalizeLaunchReadiness(trip);

  return {
    id: trip.id ?? 0,
    title: trip.title ?? "Untitled Trip",
    startDate: trip.start_date ?? "",
    endDate: trip.end_date ?? "",
    capacity: trip.capacity ?? 0,
    availableSeats: launchReadiness.availableSeats,
    descriptionRichText: normalizeTripRichText(trip.description_rich_text),
    itinerary: trip.itinerary ?? "",
    itineraryDays: normalizeTripItineraryDays(trip.itinerary_days),
    mediaItems: normalizeTripMediaItems(trip.media_items),
    packages: normalizeTripPackages(trip.packages),
    paymentSchedule: normalizeTripPaymentSchedule(trip.payment_schedule),
    confirmationRequirements: normalizeTripConfirmationRequirements(trip),
    publicationState: trip.publication_state ?? "draft",
    bookingAvailability: launchReadiness.bookingAvailability,
    manualPaymentAvailability: trip.manual_payment_availability ?? "closed",
    effectiveBookingAvailability: launchReadiness.effectiveBookingAvailability,
    publicUrlPath: trip.public_url_path ?? "",
    launchReadiness,
    tripProfilePublicationReadiness: normalizeTripProfilePublicationReadiness(
      trip.trip_profile_publication_readiness,
    ),
  };
}

export function isPublicTripPagePublished(
  trip: Pick<WorkspaceTrip, "launchReadiness" | "publicationState">,
): boolean {
  return (
    trip.launchReadiness.publicationReady ||
    trip.publicationState === "published"
  );
}

export function canPublishPublicTripPage({
  roleLabel,
  trip,
}: {
  roleLabel: string;
  trip: Pick<
    WorkspaceTrip,
    "launchReadiness" | "publicationState" | "tripProfilePublicationReadiness"
  >;
}): boolean {
  return (
    !isPublicTripPagePublished(trip) &&
    roleLabel === "Owner" &&
    trip.publicationState === "draft" &&
    trip.tripProfilePublicationReadiness.publishEligible
  );
}

export function publicTripPagePublishDisabledReason({
  roleLabel,
  trip,
}: {
  roleLabel: string;
  trip: Pick<
    WorkspaceTrip,
    "launchReadiness" | "publicationState" | "tripProfilePublicationReadiness"
  >;
}): string | undefined {
  if (isPublicTripPagePublished(trip)) {
    return undefined;
  }

  if (roleLabel !== "Owner") {
    return "Only Owners can publish the Public Trip Page.";
  }

  if (trip.publicationState !== "draft") {
    return "Only draft Public Trip Pages can be published.";
  }

  if (!trip.tripProfilePublicationReadiness.publishEligible) {
    return "Resolve Trip Profile Publication Readiness blockers first.";
  }

  return undefined;
}

type WorkspaceTripApiPayload = {
  id?: number;
  title?: string;
  start_date?: string;
  end_date?: string;
  capacity?: number;
  available_seats?: number;
  description_rich_text?: unknown;
  itinerary?: string;
  itinerary_days?: unknown;
  media_items?: unknown;
  packages?: unknown;
  payment_schedule?: unknown;
  requires_traveler_documents?: boolean;
  requires_traveler_identity_details?: boolean;
  requires_travel_logistics?: boolean;
  requires_emergency_contact?: boolean;
  requires_medical_disclosure?: boolean;
  requires_full_payment_before_confirmation?: boolean;
  confirmation_requirements_reviewed?: boolean;
  publication_state?: string;
  booking_availability?: string;
  manual_payment_availability?: string;
  effective_booking_availability?: string;
  public_url_path?: string;
  launch_readiness?: PaymentMethodReadinessApiPayload & {
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
  trip_profile_publication_readiness?: {
    blockers?: unknown;
    encouraged?: unknown;
    blocker_count?: number;
    encouraged_count?: number;
    publish_eligible?: boolean;
    lock_acknowledgement_required?: boolean;
  };
};

function normalizeLaunchReadiness(
  trip: WorkspaceTripApiPayload,
): LaunchReadinessDecision {
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

function normalizeTripProfilePublicationReadiness(
  value: WorkspaceTripApiPayload["trip_profile_publication_readiness"],
): TripProfilePublicationReadinessDecision {
  const blockers = normalizeTripProfilePublicationReadinessItems(
    value?.blockers,
  );
  const encouraged = normalizeTripProfilePublicationReadinessItems(
    value?.encouraged,
  );

  return {
    blockers,
    encouraged,
    blockerCount: value?.blocker_count ?? blockers.length,
    encouragedCount: value?.encouraged_count ?? encouraged.length,
    publishEligible: value?.publish_eligible ?? blockers.length === 0,
    lockAcknowledgementRequired: value?.lock_acknowledgement_required ?? true,
  };
}

function normalizeTripProfilePublicationReadinessItems(
  value: unknown,
): TripProfilePublicationReadinessItem[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (!isRecord(item)) {
        return null;
      }

      const id = typeof item.id === "string" ? item.id : "";
      const label = typeof item.label === "string" ? item.label : "";
      if (!id || !label) {
        return null;
      }

      return {
        id,
        label,
        detail: typeof item.detail === "string" ? item.detail : "",
        sectionId:
          typeof item.section_id === "string"
            ? item.section_id
            : typeof item.sectionId === "string"
              ? item.sectionId
              : "description",
        tone: normalizeReadinessTone(item.tone),
        blocking: item.blocking === true,
      };
    })
    .filter(
      (item): item is TripProfilePublicationReadinessItem => item !== null,
    );
}

function normalizeReadinessTone(
  value: unknown,
): TripProfilePublicationReadinessItem["tone"] {
  return value === "blocked" ||
    value === "attention" ||
    value === "clear" ||
    value === "readonly"
    ? value
    : "attention";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
