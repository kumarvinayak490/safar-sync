"use server";

import { redirect } from "next/navigation";

import { login } from "@/lib/auth";
import type { AuthActionState } from "@/lib/auth";

export async function loginAction(
  _previousState: AuthActionState,
  formData: FormData
): Promise<AuthActionState> {
  const result = await login({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? "")
  });

  if (!result.ok) {
    return { error: result.error };
  }

  redirect(result.nextRoute);
}
