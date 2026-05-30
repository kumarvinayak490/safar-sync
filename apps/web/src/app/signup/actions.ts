"use server";

import { redirect } from "next/navigation";

import { signup } from "@/lib/auth";
import type { AuthActionState } from "@/lib/auth";

export async function signupAction(
  _previousState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const result = await signup({
    fullName: String(formData.get("fullName") ?? ""),
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? "")
  });

  if (!result.ok) {
    return { error: result.error };
  }

  redirect("/onboarding/organizer");
}
