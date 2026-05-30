import assert from "node:assert/strict";
import test from "node:test";

import {
  createPublicDraftBooking,
  normalizePublicTrip,
  recordCheckoutSuccess,
  startReservationCheckout,
  submitPublicManualPaymentProof,
} from "./public-trip.ts";
import { normalizeWorkspaceTrip } from "./workspace.ts";

const gateCases = [
  {
    name: "published but closed",
    reasonCode: "booking_closed",
    ready: false,
    bookingAvailability: "closed",
    effectiveBookingAvailability: "closed",
    effectiveBookingAvailabilityLabel: "Closed",
    availabilityBand: "available",
    availabilityBandLabel: "Available",
    availableSeats: 18,
    activeSeatHolds: 0,
    bookableSeats: 18,
    message: "Bookings opening soon.",
  },
  {
    name: "missing payment method readiness",
    reasonCode: "payment_method_readiness_missing",
    ready: false,
    bookingAvailability: "open",
    effectiveBookingAvailability: "open",
    effectiveBookingAvailabilityLabel: "Open",
    availabilityBand: "available",
    availabilityBandLabel: "Available",
    availableSeats: 18,
    activeSeatHolds: 0,
    bookableSeats: 18,
    message: "Bookings opening soon.",
  },
  {
    name: "sold out",
    reasonCode: "sold_out",
    ready: false,
    bookingAvailability: "open",
    effectiveBookingAvailability: "sold_out",
    effectiveBookingAvailabilityLabel: "Sold out",
    availabilityBand: "sold_out",
    availabilityBandLabel: "Sold out",
    availableSeats: 0,
    activeSeatHolds: 0,
    bookableSeats: 0,
    message: "Sold out.",
  },
  {
    name: "ready",
    reasonCode: "ready",
    ready: true,
    bookingAvailability: "open",
    effectiveBookingAvailability: "open",
    effectiveBookingAvailabilityLabel: "Open",
    availabilityBand: "few_seats_left",
    availabilityBandLabel: "Few seats left",
    availableSeats: 2,
    activeSeatHolds: 1,
    bookableSeats: 1,
    message: "Booking can start for this trip.",
  },
] as const;

test("public trip adapter uses backend Public Booking Gate decisions", () => {
  for (const gateCase of gateCases) {
    const paymentMethodReady =
      gateCase.reasonCode !== "payment_method_readiness_missing";
    const trip = normalizePublicTrip({
      ...basePublicTripPayload(),
      booking_availability: "closed",
      effective_booking_availability: "closed",
      availability_band: "available",
      availability_band_label: "Available",
      public_booking_gate: publicBookingGatePayload(gateCase),
    });

    assert.equal(
      trip.publicBookingGate.reasonCode,
      gateCase.reasonCode,
      gateCase.name,
    );
    assert.equal(trip.publicBookingGate.ready, gateCase.ready, gateCase.name);
    assert.equal(
      trip.publicBookingGate.effectiveBookingAvailability,
      gateCase.effectiveBookingAvailability,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.availabilityBand,
      gateCase.availabilityBand,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.availableSeats,
      gateCase.availableSeats,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.activeSeatHolds,
      gateCase.activeSeatHolds,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.bookableSeats,
      gateCase.bookableSeats,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.ctaState,
      gateCase.ready ? "enabled" : "disabled",
    );
    assert.equal(
      trip.publicBookingGate.message,
      gateCase.message,
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.paymentMethodReadinessReady,
      paymentMethodReady,
      gateCase.name,
    );
    assert.deepEqual(
      trip.publicBookingGate.paymentMethods.map((method) => method.id),
      ["provider_payments", "qr_manual_payments"],
      gateCase.name,
    );
    assert.equal(
      trip.publicBookingGate.manualPaymentMethod.blockerCode,
      "manual_payment_instructions_missing",
      gateCase.name,
    );
    assert.equal(
      trip.effectiveBookingAvailability,
      gateCase.effectiveBookingAvailability,
    );
    assert.equal(trip.availabilityBand, gateCase.availabilityBand);
    assert.equal(
      trip.descriptionRichText.content[0]?.type === "paragraph"
        ? trip.descriptionRichText.content[0].content[0]?.text
        : "",
      "Traveler-facing trip description.",
    );
  }
});

test("public trip adapter hides provider checkout until Online Payment Readiness is ready", () => {
  const trip = normalizePublicTrip({
    ...basePublicTripPayload(),
    manual_payment_instructions: publicManualPaymentInstructionsPayload(),
    public_booking_gate: {
      ...publicBookingGatePayload(gateCases[3]),
      payment_method_readiness_ready: true,
      payment_method_readiness_status_label: "Ready",
      ready_payment_method_count: 1,
      ready_payment_method_ids: ["qr_manual_payments"],
      payment_methods: [
        {
          id: "provider_payments",
          label: "Online payments",
          method_type: "provider_payment",
          ready: false,
          status_label: "Blocked",
          blocker_code: "online_payment_readiness_blocked",
          blocker_label: "Online Payment Readiness blocked",
          message: "Online Payment Readiness is blocked.",
          action_label: "Pay online",
          provider: "razorpay",
          provider_label: "Razorpay",
          online_payment_readiness_ready: false,
          requires_review: false,
        },
        {
          id: "qr_manual_payments",
          label: "Manual Payments",
          method_type: "qr_manual_payment",
          ready: true,
          status_label: "Ready",
          blocker_code: "ready",
          blocker_label: "Ready",
          message: "Manual Payments are ready for this Trip.",
          action_label: "Scan QR code to pay",
          manual_payment_instructions_ready: true,
          manual_payment_availability_open: true,
          requires_review: true,
        },
      ],
      online_payment_readiness_ready: false,
      online_payment_readiness_status_label: "Blocked",
      online_payment_readiness_message: "Online Payment Readiness is blocked.",
      provider_payment_setup_complete: false,
    },
  });

  assert.equal(trip.publicBookingGate.ready, true);
  assert.equal(trip.publicBookingGate.providerPaymentMethod.ready, false);
  assert.equal(trip.publicBookingGate.manualPaymentMethod.ready, true);
  assert.equal(trip.publicBookingGate.providerCheckoutVisible, false);
  assert.equal(
    trip.publicBookingGate.primaryPaymentActionLabel,
    "Scan QR code to pay",
  );
  assert.equal(
    trip.manualPaymentInstructions?.paymentQrUrl,
    "http://localhost:8000/media/manual-payment-qr/payment-qr.png",
  );
});

test("public trip adapter does not use setup completion as checkout visibility", () => {
  const trip = normalizePublicTrip({
    ...basePublicTripPayload(),
    public_booking_gate: {
      ...publicBookingGatePayload(gateCases[1]),
      provider_payment_setup_complete: true,
      online_payment_readiness_ready: false,
      online_payment_readiness_status_label: "Blocked",
      provider_payment_method: {
        id: "provider_payments",
        label: "Online payments",
        method_type: "provider_payment",
        ready: false,
        status_label: "Blocked",
        blocker_code: "online_payment_readiness_blocked",
        blocker_label: "Online Payment Readiness blocked",
        message: "Settlement Readiness is blocked.",
        action_label: "Pay online",
        provider: "razorpay",
        provider_label: "Razorpay",
        online_payment_readiness_ready: false,
        requires_review: false,
      },
    },
  });

  assert.equal(trip.publicBookingGate.providerPaymentSetupComplete, true);
  assert.equal(trip.publicBookingGate.onlinePaymentReadinessReady, false);
  assert.equal(trip.publicBookingGate.providerCheckoutVisible, false);
  assert.equal(trip.publicBookingGate.primaryPaymentActionLabel, "Start booking");
});

test("public trip adapter drops Manual Payment Instructions unless QR manual payments are ready", () => {
  const trip = normalizePublicTrip({
    ...basePublicTripPayload(),
    manual_payment_instructions: publicManualPaymentInstructionsPayload(),
    public_booking_gate: publicBookingGatePayload(gateCases[1]),
  });

  assert.equal(trip.publicBookingGate.manualPaymentMethod.ready, false);
  assert.equal(trip.manualPaymentInstructions, null);
});

test("workspace trip adapter uses launch readiness gate decisions", () => {
  for (const gateCase of gateCases) {
    const paymentMethodReady =
      gateCase.reasonCode !== "payment_method_readiness_missing";
    const trip = normalizeWorkspaceTrip({
      id: 7,
      title: "Spiti Winter Field Week",
      start_date: "2026-10-10",
      end_date: "2026-10-15",
      capacity: 24,
      available_seats: 99,
      publication_state: "published",
      booking_availability: "closed",
      effective_booking_availability: "closed",
      public_url_path: "/trips/himalayan-monsoon-cohort/spiti-field-week",
      launch_readiness: publicBookingGatePayload(gateCase),
    });

    assert.equal(
      trip.publicUrlPath,
      "/trips/himalayan-monsoon-cohort/spiti-field-week",
    );
    assert.equal(
      trip.launchReadiness.reasonCode,
      gateCase.reasonCode,
      gateCase.name,
    );
    assert.equal(trip.launchReadiness.ready, gateCase.ready, gateCase.name);
    assert.equal(
      trip.launchReadiness.effectiveBookingAvailability,
      gateCase.effectiveBookingAvailability,
      gateCase.name,
    );
    assert.equal(
      trip.launchReadiness.availabilityBand,
      gateCase.availabilityBand,
      gateCase.name,
    );
    assert.equal(
      trip.launchReadiness.availableSeats,
      gateCase.availableSeats,
      gateCase.name,
    );
    assert.equal(
      trip.launchReadiness.activeSeatHolds,
      gateCase.activeSeatHolds,
      gateCase.name,
    );
    assert.equal(
      trip.launchReadiness.bookableSeats,
      gateCase.bookableSeats,
      gateCase.name,
    );
    assert.equal(
      trip.launchReadiness.ctaState,
      gateCase.ready ? "enabled" : "disabled",
    );
    assert.equal(
      trip.launchReadiness.paymentMethodReadinessReady,
      paymentMethodReady,
    );
    assert.deepEqual(
      trip.launchReadiness.paymentMethods.map((method) => method.id),
      ["provider_payments", "qr_manual_payments"],
    );
    assert.equal(
      trip.effectiveBookingAvailability,
      gateCase.effectiveBookingAvailability,
    );
    assert.equal(trip.availableSeats, gateCase.availableSeats);
  }
});

test("workspace trip adapter separates Razorpay and QR manual launch readiness", () => {
  const trip = normalizeWorkspaceTrip({
    id: 7,
    title: "Spiti Winter Field Week",
    start_date: "2026-10-10",
    end_date: "2026-10-15",
    capacity: 24,
    publication_state: "published",
    booking_availability: "open",
    manual_payment_availability: "open",
    public_url_path: "/trips/himalayan-monsoon-cohort/spiti-field-week",
    launch_readiness: {
      ...publicBookingGatePayload(gateCases[3]),
      payment_method_readiness_ready: true,
      ready_payment_method_count: 1,
      ready_payment_method_ids: ["qr_manual_payments"],
      provider_payment_method: {
        id: "provider_payments",
        label: "Online payments",
        method_type: "provider_payment",
        ready: false,
        status_label: "Blocked",
        blocker_code: "online_payment_readiness_blocked",
        blocker_label: "Online Payment Readiness blocked",
        message:
          "Provider verification must be verified before public booking can open.",
        action_label: "Pay online",
        provider: "razorpay",
        provider_label: "Razorpay",
        online_payment_readiness_ready: false,
        requires_review: false,
      },
      manual_payment_method: {
        id: "qr_manual_payments",
        label: "Manual Payments",
        method_type: "qr_manual_payment",
        ready: true,
        status_label: "Ready",
        blocker_code: "ready",
        blocker_label: "Ready",
        message: "This payment method is ready for public booking.",
        action_label: "Scan QR code to pay",
        manual_payment_instructions_ready: true,
        manual_payment_availability_open: true,
        requires_review: true,
      },
      payment_methods: [
        {
          id: "provider_payments",
          label: "Online payments",
          method_type: "provider_payment",
          ready: false,
          status_label: "Blocked",
          blocker_code: "online_payment_readiness_blocked",
          blocker_label: "Online Payment Readiness blocked",
          message:
            "Provider verification must be verified before public booking can open.",
          action_label: "Pay online",
          provider: "razorpay",
          provider_label: "Razorpay",
          online_payment_readiness_ready: false,
          requires_review: false,
        },
        {
          id: "qr_manual_payments",
          label: "Manual Payments",
          method_type: "qr_manual_payment",
          ready: true,
          status_label: "Ready",
          blocker_code: "ready",
          blocker_label: "Ready",
          message: "This payment method is ready for public booking.",
          action_label: "Scan QR code to pay",
          manual_payment_instructions_ready: true,
          manual_payment_availability_open: true,
          requires_review: true,
        },
      ],
      online_payment_readiness_ready: false,
      provider_payment_setup_complete: false,
    },
  });

  assert.equal(trip.manualPaymentAvailability, "open");
  assert.equal(trip.launchReadiness.paymentMethodReadinessReady, true);
  assert.equal(trip.launchReadiness.providerPaymentMethod.ready, false);
  assert.equal(trip.launchReadiness.manualPaymentMethod.ready, true);
  assert.deepEqual(trip.launchReadiness.readyPaymentMethodIds, [
    "qr_manual_payments",
  ]);
  assert.equal(
    trip.launchReadiness.manualPaymentMethod.actionLabel,
    "Scan QR code to pay",
  );
});

test("workspace trip adapter preserves Trip Profile Publication Readiness", () => {
  const trip = normalizeWorkspaceTrip({
    id: 7,
    title: "Spiti Winter Field Week",
    start_date: "2026-10-10",
    end_date: "2026-10-15",
    capacity: 24,
    publication_state: "draft",
    trip_profile_publication_readiness: {
      blocker_count: 1,
      encouraged_count: 1,
      publish_eligible: false,
      lock_acknowledgement_required: true,
      blockers: [
        {
          id: "payment-schedule",
          label: "Balance payment schedule",
          detail: "Owner review required before publication.",
          section_id: "payment-schedule",
          blocking: true,
          tone: "blocked",
        },
      ],
      encouraged: [
        {
          id: "media-gallery",
          label: "Add public media",
          detail: "Media is encouraged for the Public Trip Page.",
          section_id: "media",
          blocking: false,
          tone: "attention",
        },
      ],
    },
  });

  assert.equal(trip.tripProfilePublicationReadiness.publishEligible, false);
  assert.equal(trip.tripProfilePublicationReadiness.blockerCount, 1);
  assert.deepEqual(
    trip.tripProfilePublicationReadiness.blockers.map((item) => item.sectionId),
    ["payment-schedule"],
  );
  assert.deepEqual(
    trip.tripProfilePublicationReadiness.encouraged.map(
      (item) => item.sectionId,
    ),
    ["media"],
  );
});

test("public trip adapter prefers structured Itinerary Days while preserving legacy text", () => {
  const trip = normalizePublicTrip({
    ...basePublicTripPayload(),
    itinerary: "Day 1: legacy arrival.",
    itinerary_days: [
      {
        id: 12,
        sequence: 2,
        title: "Field day",
        date_label: "Day 2",
        description_rich_text: richTextDocument("Structured field work."),
      },
      {
        id: 11,
        sequence: 1,
        title: "Arrival",
        date_label: "Day 1",
        description_rich_text: richTextDocument("Structured arrival."),
        description_plain_text: "Structured arrival.",
      },
    ],
    public_booking_gate: publicBookingGatePayload(gateCases[0]),
  });

  assert.equal(trip.itinerary, "Day 1: legacy arrival.");
  assert.deepEqual(
    trip.itineraryDays.map((day) => ({
      sequence: day.sequence,
      title: day.title,
      dateLabel: day.dateLabel,
      descriptionPlainText: day.descriptionPlainText,
    })),
    [
      {
        sequence: 1,
        title: "Arrival",
        dateLabel: "Day 1",
        descriptionPlainText: "Structured arrival.",
      },
      {
        sequence: 2,
        title: "Field day",
        dateLabel: "Day 2",
        descriptionPlainText: "Structured field work.",
      },
    ],
  );
});

test("public trip adapter maps ordered public media gallery items", () => {
  const trip = normalizePublicTrip({
    ...basePublicTripPayload(),
    media_items: [
      {
        id: 22,
        asset_id: 8,
        image_url: "/media/trip-media/two.webp",
        position: 2,
        caption: "High valley trail",
        alt_text: "Travelers walking toward snow",
        is_public: true,
        is_cover: false,
      },
      {
        id: 21,
        asset_id: 7,
        image_url: "/media/trip-media/cover.png",
        position: 1,
        caption: "Cover ridge",
        alt_text: "Snow ridge above Kaza",
        is_public: true,
        is_cover: true,
      },
    ],
    public_booking_gate: publicBookingGatePayload(gateCases[0]),
  });

  assert.deepEqual(
    trip.mediaItems.map((item) => ({
      id: item.id,
      imageUrl: item.imageUrl,
      caption: item.caption,
      altText: item.altText,
      isCover: item.isCover,
    })),
    [
      {
        id: 21,
        imageUrl: "http://localhost:8000/media/trip-media/cover.png",
        caption: "Cover ridge",
        altText: "Snow ridge above Kaza",
        isCover: true,
      },
      {
        id: 22,
        imageUrl: "http://localhost:8000/media/trip-media/two.webp",
        caption: "High valley trail",
        altText: "Travelers walking toward snow",
        isCover: false,
      },
    ],
  );
});

test("public draft booking client sends minimum count-based intake", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedBody: Record<string, unknown> = {};

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedBody = JSON.parse(String(init?.body ?? "{}")) as Record<
      string,
      unknown
    >;
    return Response.json(
      { id: 19, draft_expires_at: "2026-05-26T18:00:00Z" },
      { status: 201 },
    );
  };

  try {
    const result = await createPublicDraftBooking({
      organizerSlug: "himalayan-monsoon-cohort",
      tripSlug: "spiti-winter-field-week",
      bookingContactName: "Asha Nair",
      bookingContactPhone: "+919876543210",
      bookingContactEmail: "asha@example.com",
      travelerCount: 2,
      packageId: 3,
    });

    const expectedUrl =
      "http://localhost:8000/api/public/trips/" +
      "himalayan-monsoon-cohort/spiti-winter-field-week/draft-bookings/";
    assert.equal(requestedUrl, expectedUrl);
    assert.deepEqual(requestedBody, {
      booking_contact_name: "Asha Nair",
      booking_contact_phone: "+919876543210",
      booking_contact_email: "asha@example.com",
      traveler_count: 2,
      package: 3,
    });
    assert.equal("traveler_slots" in requestedBody, false);
    assert.deepEqual(result, {
      ok: true,
      bookingId: 19,
      draftExpiresAt: "2026-05-26T18:00:00Z",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("reservation checkout client starts provider checkout for a Draft Booking", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedMethod = "";

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedMethod = init?.method ?? "GET";
    return Response.json(
      {
        id: 23,
        booking: 19,
        provider: "razorpay",
        purpose: "reservation",
        status: "pending",
        amount_inr: 16000,
        provider_attempt_reference: "order_reservation_checkout_001",
        checkout: {
          provider: "razorpay",
          provider_order_reference: "order_reservation_checkout_001",
          amount_inr: 16000,
          amount_minor: 1600000,
          currency: "INR",
          payment_attempt: 23,
          booking: 19,
          payment_purpose: "reservation",
          provider_payload: {
            order_id: "order_reservation_checkout_001",
            amount: 1600000,
            currency: "INR",
          },
        },
      },
      { status: 201 },
    );
  };

  try {
    const result = await startReservationCheckout(19);

    assert.equal(
      requestedUrl,
      "http://localhost:8000/api/public/bookings/19/payment-attempts/",
    );
    assert.equal(requestedMethod, "POST");
    assert.deepEqual(result, {
      ok: true,
      bookingId: 19,
      paymentAttemptId: 23,
      provider: "razorpay",
      purpose: "reservation",
      status: "pending",
      amountInr: 16000,
      providerAttemptReference: "order_reservation_checkout_001",
      checkout: {
        provider: "razorpay",
        providerOrderReference: "order_reservation_checkout_001",
        amountInr: 16000,
        amountMinor: 1600000,
        currency: "INR",
        paymentAttempt: 23,
        booking: 19,
        paymentPurpose: "reservation",
        providerPayload: {
          order_id: "order_reservation_checkout_001",
          amount: 1600000,
          currency: "INR",
        },
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("checkout success client records confirming attempt state only", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedMethod = "";
  let requestedBody: Record<string, unknown> = {};

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedMethod = init?.method ?? "GET";
    requestedBody = JSON.parse(String(init?.body ?? "{}")) as Record<
      string,
      unknown
    >;
    return Response.json(
      {
        id: 23,
        status: "confirming",
        checkout_succeeded_at: "2026-05-26T12:00:00Z",
      },
      { status: 200 },
    );
  };

  try {
    const result = await recordCheckoutSuccess(23, {
      razorpayPaymentId: "pay_browser_success_001",
      razorpayOrderId: "order_reservation_checkout_001",
      razorpaySignature: "signed_checkout_response",
    });

    assert.equal(
      requestedUrl,
      "http://localhost:8000/api/public/payment-attempts/23/checkout-success/",
    );
    assert.equal(requestedMethod, "POST");
    assert.deepEqual(requestedBody, {
      razorpay_payment_id: "pay_browser_success_001",
      razorpay_order_id: "order_reservation_checkout_001",
      razorpay_signature: "signed_checkout_response",
    });
    assert.deepEqual(result, {
      ok: true,
      paymentAttemptId: 23,
      status: "confirming",
      checkoutSucceededAt: "2026-05-26T12:00:00Z",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("public manual payment client uploads proof with count-based intake", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedMethod = "";
  let requestedBody = new FormData();
  const proof = new File(["payment-proof"], "payment-proof.png", {
    type: "image/png",
  });

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedMethod = init?.method ?? "GET";
    requestedBody = init?.body as FormData;
    return Response.json(
      {
        id: 31,
        booking: 29,
        status: "submitted",
        amount_inr: 7000,
        payment_reference: "upi-ref-101",
      },
      { status: 201 },
    );
  };

  try {
    const result = await submitPublicManualPaymentProof({
      organizerSlug: "himalayan-monsoon-cohort",
      tripSlug: "spiti-winter-field-week",
      bookingContactName: "Asha Nair",
      bookingContactPhone: "+919876543210",
      bookingContactEmail: "asha@example.com",
      travelerCount: 2,
      packageId: 3,
      paymentReference: "upi-ref-101",
      paymentProof: proof,
    });

    assert.equal(
      requestedUrl,
      "http://localhost:8000/api/public/trips/" +
        "himalayan-monsoon-cohort/spiti-winter-field-week/manual-payments/",
    );
    assert.equal(requestedMethod, "POST");
    assert.equal(requestedBody.get("booking_contact_name"), "Asha Nair");
    assert.equal(requestedBody.get("booking_contact_phone"), "+919876543210");
    assert.equal(requestedBody.get("booking_contact_email"), "asha@example.com");
    assert.equal(requestedBody.get("traveler_count"), "2");
    assert.equal(requestedBody.get("package"), "3");
    assert.equal(requestedBody.get("payment_reference"), "upi-ref-101");
    assert.equal(requestedBody.get("payment_proof"), proof);
    assert.deepEqual(result, {
      ok: true,
      bookingId: 29,
      manualPaymentId: 31,
      status: "submitted",
      amountInr: 7000,
      paymentReference: "upi-ref-101",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

function basePublicTripPayload() {
  return {
    id: 7,
    title: "Spiti Winter Field Week",
    slug: "spiti-winter-field-week",
    start_date: "2026-10-10",
    end_date: "2026-10-15",
    description_rich_text: {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "Traveler-facing trip description." },
          ],
        },
        { type: "image", attrs: { src: "https://example.test/photo.jpg" } },
      ],
    },
    confirmation_requirements_note: "Identity details and emergency contact.",
    itinerary: "Day 1: Chandigarh arrival.",
    publication_state: "published",
    publication_state_label: "Published",
    public_url_path: "/trips/himalayan-monsoon-cohort/spiti-winter-field-week",
    organizer_identity: {
      name: "Himalayan Monsoon Cohort",
      logo_url: "",
    },
    packages: [
      {
        id: 3,
        name: "Standard shared room",
        description: "Shared room package.",
        price_inr: 32000,
        reservation_amount_inr: 8000,
        position: 1,
      },
    ],
    payment_schedule: {
      reservation_milestone: {
        type: "reservation",
        due: "immediate",
        amount_source: "package_reservation_amounts",
      },
      balance_due_days_before_start: 14,
      balance_due_date: "2026-09-26",
      balance_reminder_lead_days: 3,
      has_balance_milestone: true,
    },
    updated_at: "2026-05-24T10:00:00Z",
  };
}

function publicManualPaymentInstructionsPayload() {
  return {
    ready: true,
    message: "Scan the Payment QR and submit Payment Proof for Organizer review.",
    payment_qr_url: "/media/manual-payment-qr/payment-qr.png",
    upi_id: "trips@example",
    account_name: "Himalayan Monsoon Cohort",
    bank_transfer_details: "Bank transfer reference HMC Spiti",
  };
}

function richTextDocument(text: string) {
  return {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text }],
      },
    ],
  };
}

function publicBookingGatePayload(gateCase: (typeof gateCases)[number]) {
  const paymentMethodReady =
    gateCase.reasonCode !== "payment_method_readiness_missing";
  return {
    cta_enabled: gateCase.ready,
    ready: gateCase.ready,
    reason_code: gateCase.reasonCode,
    requested_seats: 1,
    publication_ready: true,
    booking_availability_open: gateCase.bookingAvailability === "open",
    payment_method_readiness_ready: paymentMethodReady,
    payment_method_readiness_status_label: paymentMethodReady
      ? "Ready"
      : "Blocked",
    ready_payment_method_count: paymentMethodReady ? 1 : 0,
    ready_payment_method_ids: paymentMethodReady ? ["provider_payments"] : [],
    payment_methods: [
      {
        id: "provider_payments",
        label: "Online payments",
        method_type: "provider_payment",
        ready: paymentMethodReady,
        status_label: paymentMethodReady ? "Ready" : "Blocked",
        blocker_code: paymentMethodReady
          ? "ready"
          : "online_payment_readiness_blocked",
        blocker_label: paymentMethodReady
          ? "Ready"
          : "Online Payment Readiness blocked",
        message: paymentMethodReady
          ? "Online payments are ready for public booking."
          : "Provider verification must be verified before public booking can open.",
        action_label: "Pay online",
        provider: "razorpay",
        provider_label: "Razorpay",
        online_payment_readiness_ready: paymentMethodReady,
        requires_review: false,
      },
      {
        id: "qr_manual_payments",
        label: "Manual Payments",
        method_type: "qr_manual_payment",
        ready: false,
        status_label: "Blocked",
        blocker_code: "manual_payment_instructions_missing",
        blocker_label: "Manual Payment Instructions missing",
        message:
          "Manual Payments require Manual Payment Instructions before travelers can scan a Payment QR.",
        action_label: "Scan QR code to pay",
        manual_payment_instructions_ready: false,
        manual_payment_availability_open: false,
        requires_review: true,
      },
    ],
    online_payment_readiness_ready: paymentMethodReady,
    online_payment_readiness_status_label:
      gateCase.reasonCode === "payment_method_readiness_missing"
        ? "Blocked"
        : "Ready",
    online_payment_readiness_message:
      gateCase.reasonCode === "payment_method_readiness_missing"
        ? "Provider verification must be verified before public booking can open."
        : "Online Payment Readiness is ready for public booking.",
    provider_payment_setup_complete: paymentMethodReady,
    capacity_available: gateCase.availableSeats > 0,
    available_seats: gateCase.availableSeats,
    active_seat_holds: gateCase.activeSeatHolds,
    bookable_seats: gateCase.bookableSeats,
    booking_availability: gateCase.bookingAvailability,
    booking_availability_label:
      gateCase.bookingAvailability === "open" ? "Open" : "Closed",
    effective_booking_availability: gateCase.effectiveBookingAvailability,
    effective_booking_availability_label:
      gateCase.effectiveBookingAvailabilityLabel,
    availability_band: gateCase.availabilityBand,
    availability_band_label: gateCase.availabilityBandLabel,
    cta_state: gateCase.ready ? ("enabled" as const) : ("disabled" as const),
    message: gateCase.message,
  };
}
