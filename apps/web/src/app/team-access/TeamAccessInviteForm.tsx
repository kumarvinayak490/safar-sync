"use client";

import { MailPlus, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { useFormState, useFormStatus } from "react-dom";

import type {
  TeamAccessActionState,
  createInvitationAction
} from "@/app/team-access/actions";

type TeamAccessInviteFormProps = {
  action: typeof createInvitationAction;
  organizerId: number;
};

const initialState: TeamAccessActionState = {
  error: "",
  saved: false
};

export function TeamAccessInviteForm({
  action,
  organizerId
}: TeamAccessInviteFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const [role, setRole] = useState<"operator" | "owner">("operator");

  return (
    <form action={formAction} className="team-access-invite-form">
      {state.error ? (
        <div className="auth-error" role="alert">
          {state.error}
        </div>
      ) : null}
      {state.saved ? (
        <div className="identity-form-note is-saved" role="status">
          Organizer Invitation created.
        </div>
      ) : null}

      <input name="organizerId" type="hidden" value={organizerId} />

      <label>
        <span>Email</span>
        <input
          autoComplete="email"
          name="email"
          placeholder="operator@community.in"
          required
          type="email"
        />
      </label>

      <fieldset>
        <legend>Role</legend>
        <div className="team-access-role-options">
          <label>
            <input
              defaultChecked
              name="role"
              onChange={() => setRole("operator")}
              type="radio"
              value="operator"
            />
            <span>
              <strong>Operator</strong>
              <em>Trip operations access. Default for invitations.</em>
            </span>
          </label>
          <label>
            <input
              name="role"
              onChange={() => setRole("owner")}
              type="radio"
              value="owner"
            />
            <span>
              <strong>Owner</strong>
              <em>Full Organizer setup and access control.</em>
            </span>
          </label>
        </div>
      </fieldset>

      {role === "owner" ? (
        <label className="owner-access-confirmation">
          <input name="confirmOwnerPowers" required type="checkbox" value="true" />
          <span>
            <ShieldAlert aria-hidden="true" />
            <strong>Confirm Owner powers</strong>
            <em>
              Owners can manage Payment Setup, Organizer Identity, Team Access,
              users, and all Trips.
            </em>
          </span>
        </label>
      ) : null}

      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit icon-link" disabled={pending} type="submit">
      <MailPlus aria-hidden="true" />
      {pending ? "Inviting..." : "Send Invitation"}
    </button>
  );
}
