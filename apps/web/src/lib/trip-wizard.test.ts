import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTripSetupPayload,
  initialTripSetupInput,
  parseTripSetupFormData,
  tripCreationSuccessHref,
  tripSetupPath,
} from "./trip-wizard.ts";

const validInput = {
  title: "Spiti Winter Field Week",
  startDate: "2026-10-10",
  endDate: "2026-10-15",
  capacity: 24,
  packageName: "Standard shared room",
  packagePriceInr: 32000,
  reservationAmountInr: 8000,
};

test("trip draft creation builds the paid draft Trip setup payload", () => {
  const result = buildTripSetupPayload(validInput);

  assert.equal(result.ok, true);
  if (!result.ok) {
    throw new Error("Expected valid Trip setup payload.");
  }

  assert.deepEqual(result.payload, {
    title: "Spiti Winter Field Week",
    start_date: "2026-10-10",
    end_date: "2026-10-15",
    capacity: 24,
    itinerary: "",
    confirmation_requirements_note: "",
    publication_state: "draft",
    booking_availability: "closed",
    requires_traveler_documents: false,
    requires_traveler_identity_details: false,
    requires_travel_logistics: false,
    requires_emergency_contact: false,
    requires_medical_disclosure: false,
    requires_full_payment_before_confirmation: false,
    packages: [
      {
        name: "Standard shared room",
        description: "",
        price_inr: 32000,
        reservation_amount_inr: 8000,
        position: 1,
      },
    ],
    payment_schedule: {
      balance_due_days_before_start: null,
      balance_reminder_lead_days: 3,
    },
  });
});

test("trip draft creation owns fresh compact defaults", () => {
  const firstInput = initialTripSetupInput();
  const secondInput = initialTripSetupInput();

  firstInput.packageName = "Changed package";

  assert.equal(secondInput.capacity, 24);
  assert.equal(secondInput.packageName, "Standard seat");
});

test("trip setup parses compact FormData into shared draft input", () => {
  const formData = new FormData();
  formData.set("organizerId", "42");
  formData.set("title", validInput.title);
  formData.set("startDate", validInput.startDate);
  formData.set("endDate", validInput.endDate);
  formData.set("capacity", String(validInput.capacity));
  formData.set("packageName", validInput.packageName);
  formData.set("packagePriceInr", String(validInput.packagePriceInr));
  formData.set("reservationAmountInr", String(validInput.reservationAmountInr));

  assert.deepEqual(parseTripSetupFormData(formData), {
    ok: true,
    organizerId: 42,
    input: validInput,
  });
});

test("trip setup reports invalid starter Package fields before submit", () => {
  const formData = new FormData();
  formData.set("organizerId", "42");
  formData.set("title", validInput.title);
  formData.set("startDate", validInput.startDate);
  formData.set("endDate", validInput.endDate);
  formData.set("capacity", String(validInput.capacity));
  formData.set("packageName", validInput.packageName);
  formData.set("packagePriceInr", "0");
  formData.set("reservationAmountInr", String(validInput.reservationAmountInr));

  const parsed = parseTripSetupFormData(formData);

  assert.equal(parsed.ok, true);
  if (!parsed.ok) {
    throw new Error("Expected compact draft FormData to parse.");
  }
  assert.deepEqual(buildTripSetupPayload(parsed.input), {
    ok: false,
    error: "Enter a Package price greater than 0.",
  });
});

test("trip draft creation rejects invalid core fields before API submit", () => {
  assert.deepEqual(buildTripSetupPayload({ ...validInput, title: " " }), {
    ok: false,
    error: "Enter the Trip title.",
  });

  assert.deepEqual(
    buildTripSetupPayload({
      ...validInput,
      reservationAmountInr: 33000,
    }),
    {
      ok: false,
      error: "Reservation Amount cannot exceed Package price.",
    },
  );

  assert.deepEqual(
    buildTripSetupPayload({ ...validInput, endDate: "2026-10-09" }),
    {
      ok: false,
      error: "Trip end date cannot be before Trip Start Date.",
    },
  );
});

test("trip setup path keeps create route construction in one place", () => {
  assert.equal(tripSetupPath(42), "/api/organizers/42/trips/");
});

test("trip creation routes successful drafts to Trip Overview", () => {
  assert.equal(tripCreationSuccessHref(7), "/operations/trips/7/overview");
  assert.equal(tripCreationSuccessHref(0), "/trips");
});
