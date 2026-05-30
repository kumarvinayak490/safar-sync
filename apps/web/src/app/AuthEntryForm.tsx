"use client";

import Link from "next/link";
import { useFormState, useFormStatus } from "react-dom";

import type { AuthActionState } from "@/lib/auth";

type AuthEntryFormProps = {
  mode: "signup" | "login";
  action: (previousState: AuthActionState, formData: FormData) => Promise<AuthActionState>;
};

const initialState: AuthActionState = { error: "" };

export function AuthEntryForm({ action, mode }: AuthEntryFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const isSignup = mode === "signup";

  return (
    <form action={formAction} className="auth-form">
      {state.error ? (
        <div className="auth-error" role="alert">
          {state.error}
        </div>
      ) : null}

      {isSignup ? (
        <label>
          <span>Name</span>
          <input
            autoComplete="name"
            name="fullName"
            placeholder="Aarav Mehta"
            required
            type="text"
          />
        </label>
      ) : null}

      <label>
        <span>Email</span>
        <input
          autoComplete="email"
          name="email"
          placeholder="owner@community.in"
          required
          type="email"
        />
      </label>

      <label>
        <span>Password</span>
        <input
          autoComplete={isSignup ? "new-password" : "current-password"}
          minLength={8}
          name="password"
          required
          type="password"
        />
      </label>

      <SubmitButton label={isSignup ? "Create User" : "Log in"} />

      <p className="auth-switch">
        {isSignup ? "Already have a User?" : "New to TripOS?"}{" "}
        <Link href={isSignup ? "/login" : "/signup"}>
          {isSignup ? "Log in" : "Create one"}
        </Link>
      </p>
    </form>
  );
}

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit" disabled={pending} type="submit">
      {pending ? "Working..." : label}
    </button>
  );
}
