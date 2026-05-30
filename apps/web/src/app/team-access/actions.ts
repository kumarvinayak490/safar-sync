"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  acceptOrganizerInvitation,
  createOrganizerInvitation,
  resendOrganizerInvitation,
  revokeOrganizerInvitation,
  type OrganizerRole
} from "@/lib/team-access";

export type TeamAccessActionState = {
  error: string;
  saved: boolean;
};

export async function createInvitationAction(
  _previousState: TeamAccessActionState,
  formData: FormData
): Promise<TeamAccessActionState> {
  const organizerId = Number(formData.get("organizerId"));
  const role = roleFromForm(formData.get("role"));
  const result = await createOrganizerInvitation(organizerId, {
    email: String(formData.get("email") ?? ""),
    role,
    confirmOwnerPowers: formData.get("confirmOwnerPowers") === "true"
  });

  if (!result.ok) {
    return { error: result.message, saved: false };
  }

  revalidatePath("/team-access");
  revalidatePath("/home");
  return { error: "", saved: true };
}

export async function resendInvitationAction(formData: FormData): Promise<void> {
  const organizerId = Number(formData.get("organizerId"));
  const invitationId = Number(formData.get("invitationId"));
  await resendOrganizerInvitation(organizerId, invitationId);
  revalidatePath("/team-access");
}

export async function revokeInvitationAction(formData: FormData): Promise<void> {
  const organizerId = Number(formData.get("organizerId"));
  const invitationId = Number(formData.get("invitationId"));
  await revokeOrganizerInvitation(organizerId, invitationId);
  revalidatePath("/team-access");
}

export type InvitationAcceptActionState = {
  error: string;
};

export async function acceptInvitationAction(
  _previousState: InvitationAcceptActionState,
  formData: FormData
): Promise<InvitationAcceptActionState> {
  const token = String(formData.get("token") ?? "");
  const result = await acceptOrganizerInvitation(token);

  if (!result.ok) {
    return { error: result.message };
  }

  revalidatePath("/team-access");
  revalidatePath("/home");
  redirect("/home");
}

function roleFromForm(value: FormDataEntryValue | null): OrganizerRole {
  return value === "owner" ? "owner" : "operator";
}
