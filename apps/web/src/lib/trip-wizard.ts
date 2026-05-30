import { tripWorkspaceHref } from "./operations-workspace.ts";

export type TripWizardInput = {
  title: string;
  startDate: string;
  endDate: string;
  capacity: number;
  packageName: string;
  packagePriceInr: number;
  reservationAmountInr: number;
};

export type TripSetupFormParseResult =
  | {
      ok: true;
      organizerId: number;
      input: TripWizardInput;
    }
  | {
      ok: false;
      error: string;
    };

export type TripSetupPayload = {
  title: string;
  start_date: string;
  end_date: string;
  capacity: number;
  itinerary: string;
  confirmation_requirements_note: string;
  publication_state: "draft";
  booking_availability: "closed";
  requires_traveler_documents: boolean;
  requires_traveler_identity_details: boolean;
  requires_travel_logistics: boolean;
  requires_emergency_contact: boolean;
  requires_medical_disclosure: boolean;
  requires_full_payment_before_confirmation: boolean;
  packages: Array<{
    name: string;
    description: string;
    price_inr: number;
    reservation_amount_inr: number;
    position: number;
  }>;
  payment_schedule: {
    balance_due_days_before_start: number | null;
    balance_reminder_lead_days: number;
  };
};

export type TripWizardValidationResult =
  | {
      ok: true;
      payload: TripSetupPayload;
    }
  | {
      ok: false;
      error: string;
    };

export function initialTripSetupInput(): TripWizardInput {
  return {
    title: "",
    startDate: "",
    endDate: "",
    capacity: 24,
    packageName: "Standard seat",
    packagePriceInr: 32000,
    reservationAmountInr: 8000,
  };
}

export function parseTripSetupFormData(
  formData: FormData,
): TripSetupFormParseResult {
  return {
    ok: true,
    organizerId: Number(formData.get("organizerId")),
    input: {
      title: String(formData.get("title") ?? ""),
      startDate: String(formData.get("startDate") ?? ""),
      endDate: String(formData.get("endDate") ?? ""),
      capacity: Number(formData.get("capacity")),
      packageName: String(formData.get("packageName") ?? ""),
      packagePriceInr: Number(formData.get("packagePriceInr")),
      reservationAmountInr: Number(formData.get("reservationAmountInr")),
    },
  };
}

export function buildTripSetupPayload(
  input: TripWizardInput,
): TripWizardValidationResult {
  const title = input.title.trim();
  const packageName = input.packageName.trim();
  const packagePriceInr = input.packagePriceInr;
  const reservationAmountInr = input.reservationAmountInr;

  if (!title) {
    return { ok: false, error: "Enter the Trip title." };
  }

  if (!input.startDate || !input.endDate) {
    return { ok: false, error: "Enter the scheduled Trip dates." };
  }

  if (input.endDate < input.startDate) {
    return {
      ok: false,
      error: "Trip end date cannot be before Trip Start Date.",
    };
  }

  if (!Number.isInteger(input.capacity) || input.capacity < 1) {
    return { ok: false, error: "Enter a Trip Capacity of at least 1." };
  }

  if (!packageName) {
    return { ok: false, error: "Enter the Package name." };
  }

  if (!Number.isInteger(packagePriceInr) || packagePriceInr < 1) {
    return { ok: false, error: "Enter a Package price greater than 0." };
  }

  if (!Number.isInteger(reservationAmountInr) || reservationAmountInr < 1) {
    return { ok: false, error: "Enter a Reservation Amount greater than 0." };
  }

  if (reservationAmountInr > packagePriceInr) {
    return {
      ok: false,
      error: "Reservation Amount cannot exceed Package price.",
    };
  }

  return {
    ok: true,
    payload: {
      title,
      start_date: input.startDate,
      end_date: input.endDate,
      capacity: input.capacity,
      itinerary: "",
      confirmation_requirements_note: "",
      publication_state: "draft",
      booking_availability: "closed",
      requires_traveler_documents: false,
      requires_traveler_identity_details: false,
      requires_travel_logistics: false,
      requires_emergency_contact: false,
      requires_medical_disclosure: false,
      requires_full_payment_before_confirmation: false,
      packages: [
        {
          name: packageName,
          description: "",
          price_inr: packagePriceInr,
          reservation_amount_inr: reservationAmountInr,
          position: 1,
        },
      ],
      payment_schedule: {
        balance_due_days_before_start: null,
        balance_reminder_lead_days: 3,
      },
    },
  };
}

export function tripSetupPath(organizerId: number): string {
  return `/api/organizers/${organizerId}/trips/`;
}

export function tripCreationSuccessHref(tripId: number): string {
  if (!Number.isInteger(tripId) || tripId < 1) {
    return "/trips";
  }

  return tripWorkspaceHref("/overview", tripId);
}
