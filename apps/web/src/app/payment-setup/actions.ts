"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import {
  removeManualPaymentInstructions,
  runProviderConnectionTest,
  startProviderAuthorization,
  updateManualPaymentInstructions,
} from "@/lib/payment-setup";

export type ProviderAuthorizationActionState = {
  error: string;
};

export type ProviderConnectionTestActionState = {
  error: string;
  message: string;
};

export type ManualPaymentInstructionsActionState = {
  error: string;
  message: string;
};

export async function startProviderAuthorizationAction(
  _previousState: ProviderAuthorizationActionState,
  formData: FormData,
): Promise<ProviderAuthorizationActionState> {
  const organizerId = Number(formData.get("organizerId"));
  if (!Number.isFinite(organizerId) || organizerId <= 0) {
    return {
      error:
        "TripOS could not identify the Organizer for Provider Authorization.",
    };
  }

  const providerMode = String(formData.get("providerMode") ?? "test");
  const result = await startProviderAuthorization(organizerId, providerMode);

  if (!result.ok) {
    return {
      error: result.message,
    };
  }

  redirect(result.authorizationUrl);
}

export async function runProviderConnectionTestAction(
  _previousState: ProviderConnectionTestActionState,
  formData: FormData,
): Promise<ProviderConnectionTestActionState> {
  const organizerId = Number(formData.get("organizerId"));
  if (!Number.isFinite(organizerId) || organizerId <= 0) {
    return {
      error:
        "TripOS could not identify the Organizer for Provider Connection Test.",
      message: "",
    };
  }

  const result = await runProviderConnectionTest(organizerId);
  if (!result.ok) {
    return {
      error: result.message,
      message: "",
    };
  }

  revalidatePath("/payment-setup");
  return {
    error: "",
    message: `Provider Connection Test ${result.result.statusLabel.toLowerCase()}.`,
  };
}

export async function saveManualPaymentInstructionsAction(
  _previousState: ManualPaymentInstructionsActionState,
  formData: FormData,
): Promise<ManualPaymentInstructionsActionState> {
  const organizerId = Number(formData.get("organizerId"));
  if (!Number.isFinite(organizerId) || organizerId <= 0) {
    return {
      error:
        "TripOS could not identify the Organizer for Manual Payment Instructions.",
      message: "",
    };
  }

  const apiFormData = new FormData();
  for (const field of ["upi_id", "account_name", "bank_transfer_details"]) {
    apiFormData.set(field, String(formData.get(field) ?? ""));
  }

  const paymentQr = formData.get("payment_qr");
  if (paymentQr instanceof File && paymentQr.size > 0) {
    apiFormData.set("payment_qr", paymentQr);
  }

  const result = await updateManualPaymentInstructions(
    organizerId,
    apiFormData,
  );
  if (!result.ok) {
    return {
      error: result.message,
      message: "",
    };
  }

  revalidatePath("/payment-setup");
  return {
    error: "",
    message: "Manual Payment Instructions saved.",
  };
}

export async function removeManualPaymentInstructionsAction(
  _previousState: ManualPaymentInstructionsActionState,
  formData: FormData,
): Promise<ManualPaymentInstructionsActionState> {
  const organizerId = Number(formData.get("organizerId"));
  if (!Number.isFinite(organizerId) || organizerId <= 0) {
    return {
      error:
        "TripOS could not identify the Organizer for Manual Payment Instructions.",
      message: "",
    };
  }

  const result = await removeManualPaymentInstructions(organizerId);
  if (!result.ok) {
    return {
      error: result.message,
      message: "",
    };
  }

  revalidatePath("/payment-setup");
  return {
    error: "",
    message: "Manual Payment Instructions removed.",
  };
}
