import {
  authenticatedServerJsonRequest,
  extractDrfErrorMessage,
  multipartFormRequest,
} from "./drf-request.ts";
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
  type TripConfirmationRequirementsDraft,
  type TripItineraryDay,
  type TripMediaItem,
  type TripProfilePackage,
  type TripPaymentSchedule,
  type TripPaymentScheduleDraft,
} from "./trip-profile.ts";

export type SaveTripDescriptionResult =
  | {
      ok: true;
      descriptionRichText: TripRichTextDocument;
      descriptionPlainText: string;
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export type SaveTripItineraryDaysResult =
  | {
      ok: true;
      itineraryDays: TripItineraryDay[];
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export type SaveTripPackagesResult =
  | {
      ok: true;
      packages: TripProfilePackage[];
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export type SaveTripMediaGalleryResult =
  | {
      ok: true;
      mediaItems: TripMediaItem[];
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export type SaveTripPaymentScheduleResult =
  | {
      ok: true;
      paymentSchedule: TripPaymentSchedule;
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export type SaveTripConfirmationRequirementsResult =
  | {
      ok: true;
      confirmationRequirements: TripConfirmationRequirements;
      locked: boolean;
    }
  | {
      ok: false;
      message: string;
    };

export async function saveTripDescription({
  descriptionRichText,
  organizerId,
  tripId,
}: {
  descriptionRichText: TripRichTextDocument;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripDescriptionResult> {
  const result = await authenticatedServerJsonRequest<TripDescriptionApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/description/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        description_rich_text: descriptionRichText,
      },
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message: extractDrfErrorMessage(result.errorPayload) ?? "Trip Description was not saved.",
    };
  }

  return {
    ok: true,
    descriptionRichText: normalizeTripRichText(result.data.description_rich_text),
    descriptionPlainText: result.data.description_plain_text ?? "",
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function saveTripItineraryDays({
  itineraryDays,
  organizerId,
  tripId,
}: {
  itineraryDays: TripItineraryDay[];
  organizerId: number;
  tripId: number;
}): Promise<SaveTripItineraryDaysResult> {
  const result = await authenticatedServerJsonRequest<TripItineraryApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/itinerary/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        itinerary_days: itineraryDays.map((day, index) => ({
          id: day.id || undefined,
          sequence: index + 1,
          title: day.title,
          date_label: day.dateLabel,
          description_rich_text: day.descriptionRichText,
        })),
      },
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message: extractDrfErrorMessage(result.errorPayload) ?? "Itinerary Days were not saved.",
    };
  }

  return {
    ok: true,
    itineraryDays: normalizeTripItineraryDays(result.data.itinerary_days),
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function saveTripPackages({
  organizerId,
  packages,
  tripId,
}: {
  organizerId: number;
  packages: TripProfilePackage[];
  tripId: number;
}): Promise<SaveTripPackagesResult> {
  const result = await authenticatedServerJsonRequest<TripPackagesApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/packages/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        packages: packages.map((tripPackage, index) => ({
          id: tripPackage.id || undefined,
          name: tripPackage.name,
          description: tripPackage.description,
          price_inr: tripPackage.priceInr,
          reservation_amount_inr: tripPackage.reservationAmountInr,
          position: index + 1,
        })),
      },
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message: extractDrfErrorMessage(result.errorPayload) ?? "Packages were not saved.",
    };
  }

  return {
    ok: true,
    packages: normalizeTripPackages(result.data.packages),
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function uploadTripMedia({
  formData,
  organizerId,
  tripId,
}: {
  formData: FormData;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripMediaGalleryResult> {
  const result = await multipartFormRequest<TripMediaGalleryApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/media/`,
    {
      method: "POST",
      formData,
      authenticated: true,
      csrf: true,
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message:
        extractDrfErrorMessage(result.errorPayload) ??
        "Trip Media Items were not uploaded.",
    };
  }

  return {
    ok: true,
    mediaItems: normalizeTripMediaItems(result.data.media_items),
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function saveTripMediaGallery({
  mediaItems,
  organizerId,
  tripId,
}: {
  mediaItems: TripMediaItem[];
  organizerId: number;
  tripId: number;
}): Promise<SaveTripMediaGalleryResult> {
  const result = await authenticatedServerJsonRequest<TripMediaGalleryApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/media/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        media_items: mediaItems.map((item, index) => ({
          id: item.id,
          position: index + 1,
          caption: item.caption,
          alt_text: item.altText,
          is_public: item.isPublic,
          is_cover: item.isCover,
        })),
      },
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message:
        extractDrfErrorMessage(result.errorPayload) ??
        "Trip Media Gallery was not saved.",
    };
  }

  return {
    ok: true,
    mediaItems: normalizeTripMediaItems(result.data.media_items),
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function saveTripPaymentSchedule({
  organizerId,
  paymentSchedule,
  tripId,
}: {
  organizerId: number;
  paymentSchedule: TripPaymentScheduleDraft;
  tripId: number;
}): Promise<SaveTripPaymentScheduleResult> {
  const result = await authenticatedServerJsonRequest<TripPaymentScheduleApiPayload>(
    `/api/organizers/${organizerId}/trips/${tripId}/payment-schedule/`,
    {
      method: "PATCH",
      csrf: true,
      body: {
        has_balance_milestone: paymentSchedule.hasBalanceMilestone,
        balance_due_days_before_start:
          paymentSchedule.hasBalanceMilestone
            ? paymentSchedule.balanceDueDaysBeforeStart
            : null,
        balance_reminder_lead_days: paymentSchedule.balanceReminderLeadDays,
      },
    },
  );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message:
        extractDrfErrorMessage(result.errorPayload) ??
        "Balance payment schedule was not saved.",
    };
  }

  return {
    ok: true,
    paymentSchedule: normalizeTripPaymentSchedule(result.data),
    locked: result.data.trip_profile_locked ?? false,
  };
}

export async function saveTripConfirmationRequirements({
  confirmationRequirements,
  organizerId,
  tripId,
}: {
  confirmationRequirements: TripConfirmationRequirementsDraft;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripConfirmationRequirementsResult> {
  const result =
    await authenticatedServerJsonRequest<TripConfirmationRequirementsApiPayload>(
      `/api/organizers/${organizerId}/trips/${tripId}/confirmation-requirements/`,
      {
        method: "PATCH",
        csrf: true,
        body: {
          requires_traveler_documents:
            confirmationRequirements.travelerDocuments,
          requires_traveler_identity_details:
            confirmationRequirements.travelerIdentityDetails,
          requires_travel_logistics:
            confirmationRequirements.travelLogistics,
          requires_emergency_contact:
            confirmationRequirements.emergencyContact,
          requires_medical_disclosure:
            confirmationRequirements.medicalDisclosure,
          requires_full_payment_before_confirmation:
            confirmationRequirements.fullPaymentBeforeConfirmation,
        },
      },
    );

  if (!result.response.ok || !result.data) {
    return {
      ok: false,
      message:
        extractDrfErrorMessage(result.errorPayload) ??
        "Confirmation Requirements were not saved.",
    };
  }

  return {
    ok: true,
    confirmationRequirements: normalizeTripConfirmationRequirements(result.data),
    locked: result.data.trip_profile_locked ?? false,
  };
}

type TripDescriptionApiPayload = {
  description_rich_text?: unknown;
  description_plain_text?: string;
  trip_profile_locked?: boolean;
};

type TripItineraryApiPayload = {
  itinerary_days?: unknown;
  trip_profile_locked?: boolean;
};

type TripPackagesApiPayload = {
  packages?: unknown;
  trip_profile_locked?: boolean;
};

type TripMediaGalleryApiPayload = {
  media_items?: unknown;
  trip_profile_locked?: boolean;
};

type TripPaymentScheduleApiPayload = {
  has_balance_milestone?: boolean;
  balance_due_days_before_start?: number | null;
  balance_due_date?: string | null;
  balance_reminder_lead_days?: number;
  reviewed?: boolean;
  trip_profile_locked?: boolean;
};

type TripConfirmationRequirementsApiPayload = {
  requires_traveler_documents?: boolean;
  requires_traveler_identity_details?: boolean;
  requires_travel_logistics?: boolean;
  requires_emergency_contact?: boolean;
  requires_medical_disclosure?: boolean;
  requires_full_payment_before_confirmation?: boolean;
  reviewed?: boolean;
  trip_profile_locked?: boolean;
};
