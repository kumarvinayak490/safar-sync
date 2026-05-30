"use server";

import { revalidatePath } from "next/cache";

import { updateOrganizerIdentity } from "@/lib/organizer-identity";

export type OrganizerIdentityActionState = {
  error: string;
  saved: boolean;
};

export async function saveOrganizerIdentityAction(
  _previousState: OrganizerIdentityActionState,
  formData: FormData,
): Promise<OrganizerIdentityActionState> {
  const organizerId = Number(formData.get("organizerId"));
  const payload = new FormData();
  payload.set("identity_name", String(formData.get("identityName") ?? ""));
  payload.set(
    "identity_whatsapp_number",
    String(formData.get("identityWhatsappNumber") ?? ""),
  );

  const logo = formData.get("identityLogo");
  if (isNonEmptyFile(logo)) {
    payload.set("identity_logo", logo);
  }

  if (formData.get("removeIdentityLogo") === "true") {
    payload.set("remove_identity_logo", "true");
  }

  const result = await updateOrganizerIdentity(organizerId, payload);
  if (!result.ok) {
    return {
      error: result.message,
      saved: false,
    };
  }

  revalidatePath("/organizer-identity");
  revalidatePath("/home");

  return {
    error: "",
    saved: true,
  };
}

function isNonEmptyFile(value: FormDataEntryValue | null): value is File {
  return value !== null && typeof value === "object" && "size" in value && value.size > 0;
}
