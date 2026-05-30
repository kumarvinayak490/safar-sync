"use server";

import { revalidatePath } from "next/cache";

import { tripWorkspaceHref } from "@/lib/operations-workspace";
import {
  saveTripDescription,
  saveTripConfirmationRequirements,
  saveTripItineraryDays,
  saveTripMediaGallery,
  saveTripPackages,
  saveTripPaymentSchedule,
  uploadTripMedia,
  type SaveTripDescriptionResult,
  type SaveTripConfirmationRequirementsResult,
  type SaveTripItineraryDaysResult,
  type SaveTripMediaGalleryResult,
  type SaveTripPackagesResult,
  type SaveTripPaymentScheduleResult,
} from "@/lib/trip-profile-api";
import type {
  TripItineraryDay,
  TripConfirmationRequirementsDraft,
  TripMediaItem,
  TripPaymentScheduleDraft,
  TripProfilePackage,
} from "@/lib/trip-profile";
import type { TripRichTextDocument } from "@/lib/trip-rich-text";

export async function saveTripDescriptionAction({
  descriptionRichText,
  organizerId,
  tripId,
}: {
  descriptionRichText: TripRichTextDocument;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripDescriptionResult> {
  const result = await saveTripDescription({
    descriptionRichText,
    organizerId,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function saveTripItineraryDaysAction({
  itineraryDays,
  organizerId,
  tripId,
}: {
  itineraryDays: TripItineraryDay[];
  organizerId: number;
  tripId: number;
}): Promise<SaveTripItineraryDaysResult> {
  const result = await saveTripItineraryDays({
    itineraryDays,
    organizerId,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function saveTripPackagesAction({
  organizerId,
  packages,
  tripId,
}: {
  organizerId: number;
  packages: TripProfilePackage[];
  tripId: number;
}): Promise<SaveTripPackagesResult> {
  const result = await saveTripPackages({
    organizerId,
    packages,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function uploadTripMediaAction({
  formData,
  organizerId,
  tripId,
}: {
  formData: FormData;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripMediaGalleryResult> {
  const result = await uploadTripMedia({
    formData,
    organizerId,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function saveTripMediaGalleryAction({
  mediaItems,
  organizerId,
  tripId,
}: {
  mediaItems: TripMediaItem[];
  organizerId: number;
  tripId: number;
}): Promise<SaveTripMediaGalleryResult> {
  const result = await saveTripMediaGallery({
    mediaItems,
    organizerId,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function saveTripPaymentScheduleAction({
  organizerId,
  paymentSchedule,
  tripId,
}: {
  organizerId: number;
  paymentSchedule: TripPaymentScheduleDraft;
  tripId: number;
}): Promise<SaveTripPaymentScheduleResult> {
  const result = await saveTripPaymentSchedule({
    organizerId,
    paymentSchedule,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}

export async function saveTripConfirmationRequirementsAction({
  confirmationRequirements,
  organizerId,
  tripId,
}: {
  confirmationRequirements: TripConfirmationRequirementsDraft;
  organizerId: number;
  tripId: number;
}): Promise<SaveTripConfirmationRequirementsResult> {
  const result = await saveTripConfirmationRequirements({
    confirmationRequirements,
    organizerId,
    tripId,
  });

  if (result.ok) {
    revalidatePath(tripWorkspaceHref("/trip-profile", tripId));
    revalidatePath(tripWorkspaceHref("/launch", tripId));
    revalidatePath(tripWorkspaceHref("/overview", tripId));
  }

  return result;
}
