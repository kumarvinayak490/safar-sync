"use client";

import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useFormState, useFormStatus } from "react-dom";

import {
  parseRequiredNumberInput,
  requiredNumberInputValue,
} from "@/lib/number-input";
import type { TripWizardActionState } from "@/lib/trip-wizard-server";
import type { TripWizardInput } from "@/lib/trip-wizard";
import {
  buildTripSetupPayload,
  initialTripSetupInput,
} from "@/lib/trip-wizard";

type TripDraftCreationFormProps = {
  action: (
    previousState: TripWizardActionState,
    formData: FormData,
  ) => Promise<TripWizardActionState>;
  organizerId: number;
  organizerName: string;
};

const initialState: TripWizardActionState = { error: "" };

export function TripDraftCreationForm({
  action,
  organizerId,
  organizerName,
}: TripDraftCreationFormProps) {
  const [serverState, formAction] = useFormState(action, initialState);
  const [localError, setLocalError] = useState("");
  const [input, setInput] = useState<TripWizardInput>(initialTripSetupInput);
  const validation = useMemo(() => buildTripSetupPayload(input), [input]);
  const currentError = localError || serverState.error;

  function updateField<Key extends keyof TripWizardInput>(
    key: Key,
    value: TripWizardInput[Key],
  ) {
    setInput((current) => ({ ...current, [key]: value }));
    setLocalError("");
  }

  function beforeSubmit(event: FormEvent<HTMLFormElement>) {
    if (!validation.ok) {
      event.preventDefault();
      setLocalError(validation.error);
    }
  }

  return (
    <form
      action={formAction}
      className="trip-draft-form"
      onSubmit={beforeSubmit}
    >
      <input name="organizerId" type="hidden" value={organizerId} />

      <div className="trip-draft-form-heading">
        <div>
          <span>Draft Trip</span>
          <strong>{organizerName}</strong>
        </div>
        <p>Title, dates, capacity, and one starter Package.</p>
      </div>

      {currentError ? (
        <div className="auth-error" role="alert">
          {currentError}
        </div>
      ) : null}

      <div className="trip-draft-grid">
        <fieldset className="trip-draft-fieldset">
          <legend>Basics</legend>
          <label className="span-2">
            <span>Trip title</span>
            <input
              maxLength={180}
              name="title"
              onChange={(event) => updateField("title", event.target.value)}
              placeholder="Spiti Winter Field Week"
              required
              type="text"
              value={input.title}
            />
          </label>
          <label>
            <span>Trip Start Date</span>
            <input
              name="startDate"
              onChange={(event) => updateField("startDate", event.target.value)}
              required
              type="date"
              value={input.startDate}
            />
          </label>
          <label>
            <span>Trip End Date</span>
            <input
              name="endDate"
              onChange={(event) => updateField("endDate", event.target.value)}
              required
              type="date"
              value={input.endDate}
            />
          </label>
          <label>
            <span>Trip Capacity</span>
            <input
              min={1}
              name="capacity"
              onChange={(event) =>
                updateField(
                  "capacity",
                  parseRequiredNumberInput(event.target.value),
                )
              }
              required
              type="number"
              value={requiredNumberInputValue(input.capacity)}
            />
          </label>
        </fieldset>

        <fieldset className="trip-draft-fieldset">
          <legend>Starter Package</legend>
          <label className="span-2">
            <span>Package name</span>
            <input
              maxLength={140}
              name="packageName"
              onChange={(event) =>
                updateField("packageName", event.target.value)
              }
              required
              type="text"
              value={input.packageName}
            />
          </label>
          <label>
            <span>Package price</span>
            <input
              min={1}
              name="packagePriceInr"
              onChange={(event) =>
                updateField(
                  "packagePriceInr",
                  parseRequiredNumberInput(event.target.value),
                )
              }
              required
              type="number"
              value={requiredNumberInputValue(input.packagePriceInr)}
            />
          </label>
          <label>
            <span>Reservation Amount</span>
            <input
              min={1}
              name="reservationAmountInr"
              onChange={(event) =>
                updateField(
                  "reservationAmountInr",
                  parseRequiredNumberInput(event.target.value),
                )
              }
              required
              type="number"
              value={requiredNumberInputValue(input.reservationAmountInr)}
            />
          </label>
        </fieldset>
      </div>

      <div className="trip-draft-footer">
        <div>
          <span>Next</span>
          <strong>Trip Overview</strong>
          <em>Trip Profile stays editable before Launch.</em>
        </div>
        <SubmitButton />
      </div>
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button className="auth-submit" disabled={pending} type="submit">
      {pending ? "Creating Trip..." : "Create Draft Trip"}
    </button>
  );
}
