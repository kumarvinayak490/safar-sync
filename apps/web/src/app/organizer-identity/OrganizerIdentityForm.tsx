"use client";

import { Image as ImageIcon, Save, Trash2, Upload } from "lucide-react";
import { useFormState, useFormStatus } from "react-dom";

import type { OrganizerIdentityActionState } from "@/app/organizer-identity/actions";
import type { OrganizerIdentity } from "@/lib/organizer-identity";

type OrganizerIdentityFormProps = {
  action: (
    previousState: OrganizerIdentityActionState,
    formData: FormData,
  ) => Promise<OrganizerIdentityActionState>;
  canManage: boolean;
  identity: OrganizerIdentity;
  organizerId: number;
};

const initialState: OrganizerIdentityActionState = {
  error: "",
  saved: false,
};

export function OrganizerIdentityForm({
  action,
  canManage,
  identity,
  organizerId,
}: OrganizerIdentityFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const [removeState, removeFormAction] = useFormState(action, initialState);

  if (!canManage) {
    return (
      <div className="identity-readonly-panel" aria-label="Organizer Identity access">
        <span>Access</span>
        <strong>Read-only for Operators</strong>
        <p>
          Operators can view traveler-facing identity and WhatsApp contact. An
          Owner manages Organizer Identity.
        </p>
      </div>
    );
  }

  return (
    <div className="identity-edit-stack">
      <form action={formAction} className="identity-settings-form">
        {state.error ? (
          <div className="auth-error" role="alert">
            {state.error}
          </div>
        ) : null}
        {state.saved ? (
          <div className="identity-form-note is-saved" role="status">
            Organizer Identity saved.
          </div>
        ) : null}

        <input name="organizerId" type="hidden" value={organizerId} />

        <label>
          <span>Traveler-facing name</span>
          <input
            autoComplete="organization"
            defaultValue={identity.name}
            maxLength={160}
            name="identityName"
            required
            type="text"
          />
        </label>

        <label>
          <span>WhatsApp number</span>
          <input
            autoComplete="tel"
            defaultValue={identity.whatsappNumber}
            inputMode="tel"
            maxLength={40}
            name="identityWhatsappNumber"
            placeholder="+91 98765 43210"
            type="tel"
          />
          <em>
            Traveler questions on the public Trip Page will open this WhatsApp
            number.
          </em>
        </label>

        <label className="identity-upload-control">
          <span>Organizer Logo</span>
          <div>
            <Upload aria-hidden="true" />
            <strong>
              {identity.logoUploaded ? "Replace logo file" : "Upload logo file"}
            </strong>
            <em>PNG, JPG, or WebP. Maximum 2 MB.</em>
          </div>
          <input accept="image/png,image/jpeg,image/webp" name="identityLogo" type="file" />
        </label>

        <SubmitButton />
      </form>

      {identity.logoUploaded ? (
        <form action={removeFormAction} className="identity-remove-form">
          {removeState.error ? (
            <div className="auth-error" role="alert">
              {removeState.error}
            </div>
          ) : null}
          {removeState.saved ? (
            <div className="identity-form-note is-saved" role="status">
              Organizer Logo removed.
            </div>
          ) : null}
          <input name="organizerId" type="hidden" value={organizerId} />
          <input name="identityName" type="hidden" value={identity.name} />
          <input
            name="identityWhatsappNumber"
            type="hidden"
            value={identity.whatsappNumber}
          />
          <input name="removeIdentityLogo" type="hidden" value="true" />
          <div>
            <ImageIcon aria-hidden="true" />
            <span>Organizer Logo is optional. Removing it keeps the text fallback active.</span>
          </div>
          <RemoveButton />
        </form>
      ) : null}
    </div>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit icon-link" disabled={pending} type="submit">
      <Save aria-hidden="true" />
      {pending ? "Saving..." : "Save Identity"}
    </button>
  );
}

function RemoveButton() {
  const { pending } = useFormStatus();

  return (
    <button className="identity-danger-button icon-link" disabled={pending} type="submit">
      <Trash2 aria-hidden="true" />
      {pending ? "Removing..." : "Remove Organizer Logo"}
    </button>
  );
}
