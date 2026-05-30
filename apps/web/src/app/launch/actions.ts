"use server";

import { revalidatePath } from "next/cache";

import { updateTripLaunchState } from "@/lib/operations-dashboard";
import { tripWorkspaceHref } from "@/lib/operations-workspace";

function revalidateLaunchSurfaces(
  tripId: number,
  publicUrlPath: string | null,
  currentPath?: FormDataEntryValue | null,
) {
  const pathsToRevalidate = new Set([
    tripWorkspaceHref("/launch", tripId),
    tripWorkspaceHref("/overview", tripId),
    tripWorkspaceHref("/trip-profile", tripId),
  ]);

  if (
    typeof currentPath === "string" &&
    currentPath.startsWith(`/operations/trips/${tripId}/`)
  ) {
    pathsToRevalidate.add(currentPath);
  }

  if (publicUrlPath) {
    pathsToRevalidate.add(publicUrlPath);
  }

  for (const path of pathsToRevalidate) {
    revalidatePath(path);
  }
}

export async function publishPublicTripPageAction(formData: FormData) {
  const tripId = Number(formData.get("tripId"));
  const currentPath = formData.get("currentPath");

  const { publicUrlPath } = await updateTripLaunchState({
    organizerId: Number(formData.get("organizerId")),
    tripId,
    publicationState: "published",
    publishLockAcknowledged: formData.get("publishLockAcknowledged") === "on",
  });

  revalidateLaunchSurfaces(tripId, publicUrlPath, currentPath);
}

export async function openPublicBookingAction(formData: FormData) {
  const tripId = Number(formData.get("tripId"));

  const { publicUrlPath } = await updateTripLaunchState({
    organizerId: Number(formData.get("organizerId")),
    tripId,
    bookingAvailability: "open",
    manualPaymentAvailability:
      formData.get("openManualPayments") === "on" ? "open" : undefined,
  });

  revalidateLaunchSurfaces(tripId, publicUrlPath);
}

export async function setManualPaymentAvailabilityAction(formData: FormData) {
  const tripId = Number(formData.get("tripId"));
  const manualPaymentAvailability =
    formData.get("manualPaymentAvailability") === "open" ? "open" : "closed";
  const openBookingTogether = formData.get("openBookingTogether") === "on";

  const { publicUrlPath } = await updateTripLaunchState({
    organizerId: Number(formData.get("organizerId")),
    tripId,
    ...(manualPaymentAvailability === "open" && openBookingTogether
      ? {
          bookingAvailability: "open",
          manualPaymentAvailability: "open",
        }
      : { manualPaymentAvailability }),
  });

  revalidateLaunchSurfaces(tripId, publicUrlPath);
}
