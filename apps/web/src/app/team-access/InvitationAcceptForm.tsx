"use client";

import { UserCheck } from "lucide-react";
import { useFormState, useFormStatus } from "react-dom";

import type {
  InvitationAcceptActionState,
  acceptInvitationAction
} from "@/app/team-access/actions";

const initialState: InvitationAcceptActionState = {
  error: ""
};

export function InvitationAcceptForm({
  action,
  token
}: {
  action: typeof acceptInvitationAction;
  token: string;
}) {
  const [state, formAction] = useFormState(action, initialState);

  return (
    <form action={formAction} className="team-access-accept-form">
      {state.error ? (
        <div className="auth-error" role="alert">
          {state.error}
        </div>
      ) : null}
      <input name="token" type="hidden" value={token} />
      <AcceptButton />
    </form>
  );
}

function AcceptButton() {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit icon-link" disabled={pending} type="submit">
      <UserCheck aria-hidden="true" />
      {pending ? "Accepting..." : "Accept Invitation"}
    </button>
  );
}
