"use server";

import { redirect } from "next/navigation";

import { createOrganizer } from "@/lib/auth";
import type { AuthActionState } from "@/lib/auth";

export async function createOrganizerAction(
  _previousState: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const result = await createOrganizer({
    name: String(formData.get("name") ?? ""),
  });

  if (!result.ok) {
    return { error: result.error };
  }

  redirect(result.nextRoute);
}
