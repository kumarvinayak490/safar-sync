"use server";

import { redirect } from "next/navigation";

import {
  TripWizardActionState,
  createTripFromSetupForm
} from "@/lib/trip-wizard-server";
import { tripCreationSuccessHref } from "@/lib/trip-wizard";

export async function createTripAction(
  _previousState: TripWizardActionState,
  formData: FormData
): Promise<TripWizardActionState> {
  const result = await createTripFromSetupForm(formData);

  if (!result.ok) {
    return { error: result.error };
  }

  redirect(tripCreationSuccessHref(result.tripId));
}
