"use server";

import {
  DrfRequestResult,
  authenticatedServerJsonRequest,
  extractDrfErrorMessage
} from "@/lib/drf-request";
import {
  TripWizardInput,
  buildTripSetupPayload,
  parseTripSetupFormData,
  tripSetupPath
} from "@/lib/trip-wizard";

export type TripWizardActionState = {
  error: string;
};

export type TripWizardResult =
  | {
      ok: true;
      tripId: number;
    }
  | {
      ok: false;
      error: string;
    };

export async function createTripFromSetupForm(formData: FormData): Promise<TripWizardResult> {
  const parsed = parseTripSetupFormData(formData);

  if (!parsed.ok) {
    return { ok: false, error: parsed.error };
  }

  return createTripFromWizard(parsed.organizerId, parsed.input);
}

export async function createTripFromWizard(
  organizerId: number,
  input: TripWizardInput
): Promise<TripWizardResult> {
  if (!Number.isInteger(organizerId) || organizerId < 1) {
    return { ok: false, error: "Trip creation needs an Organizer." };
  }

  const built = buildTripSetupPayload(input);
  if (!built.ok) {
    return built;
  }

  let result: DrfRequestResult<{ id?: unknown }>;
  try {
    result = await authenticatedServerJsonRequest<{ id?: unknown }>(tripSetupPath(organizerId), {
      method: "POST",
      body: built.payload,
      csrf: true
    });
  } catch {
    return {
      ok: false,
      error: "TripOS could not reach the local trip setup service. Start the API and try again."
    };
  }

  if (!result.response.ok) {
    return {
      ok: false,
      error: tripWizardErrorMessage(result.response.status, result.errorPayload)
    };
  }

  return {
    ok: true,
    tripId: typeof result.data?.id === "number" ? result.data.id : 0
  };
}

function tripWizardErrorMessage(status: number, payload: unknown): string {
  const firstMessage = extractDrfErrorMessage(payload, [
    "non_field_errors",
    "detail",
    "title",
    "start_date",
    "end_date",
    "capacity",
    "packages",
    "payment_schedule"
  ]);

  if (status === 400 && firstMessage) {
    return firstMessage;
  }

  if ((status === 401 || status === 403) && firstMessage) {
    return firstMessage;
  }

  if (status === 401 || status === 403) {
    return "Only an Owner can create Trips for this Organizer.";
  }

  if (status >= 500) {
    return "TripOS could not complete Trip setup. Try again after the API is healthy.";
  }

  return "TripOS could not create this Trip. Check the setup and try again.";
}
