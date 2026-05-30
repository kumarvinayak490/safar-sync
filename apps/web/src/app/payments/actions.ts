"use server";

import { revalidatePath } from "next/cache";

import { authenticatedServerJsonRequest } from "@/lib/drf-request";
import { tripWorkspaceHref } from "@/lib/operations-workspace";

export async function approveManualPaymentAction(formData: FormData) {
  await decideManualPayment(formData, "approve");
}

export async function rejectManualPaymentAction(formData: FormData) {
  await decideManualPayment(formData, "reject");
}

async function decideManualPayment(
  formData: FormData,
  decision: "approve" | "reject",
) {
  const organizerId = Number(formData.get("organizerId"));
  const tripId = Number(formData.get("tripId"));
  const manualPaymentId = Number(formData.get("manualPaymentId"));

  if (
    !Number.isFinite(organizerId) ||
    organizerId <= 0 ||
    !Number.isFinite(tripId) ||
    tripId <= 0 ||
    !Number.isFinite(manualPaymentId) ||
    manualPaymentId <= 0
  ) {
    throw new Error("TripOS could not identify the Manual Payment.");
  }

  const result = await authenticatedServerJsonRequest(
    `/api/operations/organizers/${organizerId}/manual-payments/${manualPaymentId}/${decision}/`,
    {
      method: "POST",
      csrf: true,
      body:
        decision === "reject"
          ? {
              rejection_reason:
                "Rejected from the Manual Payments approval queue.",
            }
          : {},
    },
  );

  if (!result.response.ok) {
    const decisionLabel = decision === "approve" ? "approved" : "rejected";

    throw new Error(
      result.errorMessage ?? `Manual Payment could not be ${decisionLabel}.`,
    );
  }

  revalidatePath(tripWorkspaceHref("/payments", tripId));
  revalidatePath(tripWorkspaceHref("/bookings", tripId));
  revalidatePath(tripWorkspaceHref("/overview", tripId));
}
