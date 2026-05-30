"use client";

import { useFormState, useFormStatus } from "react-dom";

import type { AuthActionState } from "@/lib/auth";

type OrganizerOnboardingFormProps = {
  action: (
    previousState: AuthActionState,
    formData: FormData,
  ) => Promise<AuthActionState>;
  ownerName: string;
};

const initialState: AuthActionState = { error: "" };

export function OrganizerOnboardingForm({
  action,
  ownerName,
}: OrganizerOnboardingFormProps) {
  const [state, formAction] = useFormState(action, initialState);

  return (
    <form action={formAction} className="onboarding-form">
      {state.error ? (
        <div className="auth-error" role="alert">
          {state.error}
        </div>
      ) : null}

      <label>
        <span>Organizer name</span>
        <input
          autoComplete="organization"
          maxLength={160}
          name="name"
          placeholder="Western Ghats Weekenders"
          required
          type="text"
        />
      </label>

      <div className="owner-confirmation" aria-label="Owner assignment">
        <span>Owner User</span>
        <strong>{ownerName}</strong>
        <em>
          This User becomes the first Owner. TripOS uses the Organizer name as
          the public Organizer Identity until an Owner changes it later.
        </em>
      </div>

      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit" disabled={pending} type="submit">
      {pending ? "Creating Organizer..." : "Create Organizer and enter Home"}
    </button>
  );
}
