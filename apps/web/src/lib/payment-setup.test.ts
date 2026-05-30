import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeProviderConnectionTestResults,
  normalizeOrganizerPaymentSetup,
  normalizePaymentSetupStatus,
  paymentSetupActionKind,
  providerAuthorizationActionKind,
} from "./payment-setup.ts";

test("Payment Setup adapter preserves Organizer setup labels and provider readiness", () => {
  const setup = normalizeOrganizerPaymentSetup({
    status: {
      provider: "razorpay",
      provider_label: "Razorpay",
      provider_disclosure:
        "Razorpay processes provider-confirmed payments and provider verification for the India MVP.",
      payout_status: "pending",
      payout_status_label: "Pending",
      settlement_readiness_status: "pending",
      settlement_readiness_status_label: "Pending",
      settlement_readiness_ready: false,
      provider_payment_setup_status: "action_required",
      provider_payment_setup_status_label: "Action required",
      provider_payment_setup_complete: false,
      provider_authorization_method: "oauth",
      provider_authorization_method_label: "OAuth Provider Authorization",
      provider_authorization_state: "action_required",
      provider_authorization_state_label: "Action required",
      online_payment_readiness_ready: false,
      online_payment_readiness_status_label: "Blocked",
      online_payment_readiness_blocker_code:
        "provider_verification_not_verified",
      online_payment_readiness_blocker_label:
        "Provider verification not verified",
      online_payment_readiness_message:
        "Provider verification must be verified before public booking can open.",
      provider_verification_status: "action_required",
      provider_verification_status_label: "Action required",
      payout_account_ready: false,
      provider_payment_capability_enabled: false,
      provider_connection_state: "unhealthy",
      provider_connection_state_label: "Unhealthy",
      provider_mode: "test",
      provider_mode_label: "Test",
      provider_order_creation_available: false,
      can_manage_provider_authorization: true,
      payment_setup_access_message:
        "Owners can connect Razorpay or use recovery actions to restore Online Payment Readiness.",
      provider_authorization_actions: [
        {
          id: "connect",
          label: "Connect with Razorpay",
          description:
            "Start OAuth Provider Authorization on Razorpay-hosted screens.",
          status_label: "Available",
          enabled: true,
          tone: "primary",
        },
        {
          id: "retry",
          label: "Retry authorization",
          description:
            "Refresh Provider Authorization after revoked or unhealthy access.",
          status_label: "Recovery",
          enabled: true,
          tone: "secondary",
        },
        {
          id: "test_connection",
          label: "Test connection",
          description:
            "Run a Provider Connection Test without creating bookings or ledger entries.",
          status_label: "Available",
          enabled: true,
          tone: "secondary",
        },
      ],
      manual_payment_capability_enabled: true,
      individual_creator_payment_path: {
        title: "Individual Creator Payment Path",
        summary:
          "Creator-led Organizers can connect a provider account that matches how they already collect trip payments.",
        steps: [
          "Use a published TripOS Public Trip URL to show the provider where travelers will review the trip and pay.",
        ],
      },
      provider_verification_url: {
        available: true,
        source: "public_trip_url",
        source_label: "TripOS Public Trip URL",
        url_path: "/trips/himalayan-monsoon-cohort/spiti-field-week",
        trip_id: 7,
        trip_title: "Spiti Winter Field Week",
        status_label: "Ready to share",
        message:
          "Use this published TripOS Public Trip URL as the Provider Verification URL.",
      },
      manual_payments_only: {
        supported: true,
        active: true,
        status_label: "Manual Payments Only",
        public_booking_message:
          "Public Booking stays closed with Bookings Opening Soon until Online Payment Readiness is ready.",
        manual_operations_message:
          "Manual Bookings and Manual Payments remain available in the Operations Dashboard.",
      },
    },
    payoutAccount: {
      holder_name: "Field Team Collective",
      provider_account_reference: "acc_razorpay_pilot",
      status: "pending",
      status_label: "Pending",
      notes: "Waiting on account verification.",
      updated_at: "2026-05-24T10:00:00Z",
    },
    providerPaymentSetup: {
      provider: "razorpay",
      provider_label: "Razorpay",
      provider_disclosure:
        "Razorpay processes provider-confirmed payments and provider verification for the India MVP.",
      status: "action_required",
      status_label: "Action required",
      provider_merchant_reference: "merchant_123",
      authorization_method: "oauth",
      authorization_method_label: "OAuth Provider Authorization",
      authorization_state: "action_required",
      authorization_state_label: "Action required",
      provider_verification_status: "action_required",
      provider_verification_status_label: "Action required",
      provider_payment_capability_enabled: false,
      provider_connection_state: "unhealthy",
      provider_connection_state_label: "Unhealthy",
      provider_mode: "test",
      provider_mode_label: "Test",
      is_complete: false,
      updated_at: "2026-05-24T10:00:00Z",
    },
    providerConnectionTests: [
      {
        id: 41,
        provider: "razorpay",
        provider_label: "Razorpay",
        provider_mode: "test",
        provider_mode_label: "Test",
        status: "succeeded",
        status_label: "Succeeded",
        provider_account_reference: "merchant_123",
        checks: {
          credentials: { status: "passed" },
          order_creation: { status: "passed" },
          oauth_token_refresh: { status: "skipped" },
        },
        failure_reason: "",
        initiated_by_email: "owner@example.com",
        initiated_by_staff: false,
        started_at: "2026-05-29T02:45:00Z",
        completed_at: "2026-05-29T02:45:03Z",
      },
    ],
  });

  assert.equal(setup.status.providerPaymentSetupStatusLabel, "Action required");
  assert.equal(setup.status.providerAuthorizationStateLabel, "Action required");
  assert.equal(setup.status.settlementReadinessStatusLabel, "Pending");
  assert.equal(setup.status.settlementReadinessReady, false);
  assert.equal(setup.status.providerPaymentSetupComplete, false);
  assert.equal(setup.status.onlinePaymentReadinessReady, false);
  assert.equal(setup.status.onlinePaymentReadinessStatusLabel, "Blocked");
  assert.equal(setup.status.paymentMethodReadinessReady, false);
  assert.equal(setup.status.readyPaymentMethodCount, 0);
  assert.equal(setup.status.providerOrderCreationAvailable, false);
  assert.deepEqual(
    setup.status.paymentMethods.map((method) => method.id),
    ["provider_payments", "qr_manual_payments"],
  );
  assert.equal(
    setup.status.manualPaymentMethod.blockerCode,
    "manual_payment_instructions_missing",
  );
  assert.equal(setup.status.manualPaymentInstructions.ready, false);
  assert.equal(
    setup.status.manualPaymentInstructions.blockerLabel,
    "Payment QR missing",
  );
  assert.equal(setup.status.canManageManualPaymentInstructions, false);
  assert.equal(setup.payoutAccount.holderName, "Field Team Collective");
  assert.equal(setup.providerPaymentSetup.providerLabel, "Razorpay");
  assert.equal(
    setup.providerPaymentSetup.authorizationMethodLabel,
    "OAuth Provider Authorization",
  );
  assert.equal(
    setup.providerPaymentSetup.providerMerchantReference,
    "merchant_123",
  );
  assert.equal(
    setup.status.individualCreatorPaymentPath.title,
    "Individual Creator Payment Path",
  );
  assert.match(
    setup.status.individualCreatorPaymentPath.summary,
    /provider account/i,
  );
  assert.equal(
    setup.status.providerVerificationUrl.urlPath,
    "/trips/himalayan-monsoon-cohort/spiti-field-week",
  );
  assert.equal(
    setup.status.providerVerificationUrl.statusLabel,
    "Ready to share",
  );
  assert.equal(setup.status.manualPaymentsOnly.active, true);
  assert.equal(
    setup.status.manualPaymentsOnly.statusLabel,
    "Manual Payments Only",
  );
  assert.match(
    setup.status.manualPaymentsOnly.publicBookingMessage,
    /Bookings Opening Soon/,
  );
  assert.equal(setup.status.canManageProviderAuthorization, true);
  assert.deepEqual(
    setup.status.providerAuthorizationActions.map((action) => action.id),
    ["connect", "retry", "test_connection"],
  );
  assert.equal(setup.status.providerAuthorizationActions[0]?.enabled, true);
  assert.equal(setup.providerConnectionTests[0]?.statusLabel, "Succeeded");
  assert.equal(setup.providerConnectionTests[0]?.passedCheckCount, 2);
  assert.equal(setup.providerConnectionTests[0]?.skippedCheckCount, 1);
});

test("Payment Setup status adapter defaults to incomplete without blocking manual payments", () => {
  const status = normalizePaymentSetupStatus(null);

  assert.equal(status.payoutStatus, "not_started");
  assert.equal(status.settlementReadinessStatus, "not_started");
  assert.equal(status.settlementReadinessReady, false);
  assert.equal(status.providerLabel, "Razorpay");
  assert.equal(status.providerAuthorizationMethod, "oauth");
  assert.equal(status.providerPaymentSetupStatus, "not_started");
  assert.equal(status.providerPaymentSetupComplete, false);
  assert.equal(status.onlinePaymentReadinessReady, false);
  assert.equal(status.paymentMethodReadinessReady, false);
  assert.equal(status.manualPaymentMethod.actionLabel, "Scan QR code to pay");
  assert.equal(status.manualPaymentInstructions.paymentQrUploaded, false);
  assert.equal(
    status.manualPaymentInstructions.message,
    "Manual Payment Instructions need a Payment QR before Manual Payments can be offered from Launch.",
  );
  assert.equal(status.manualPaymentCapabilityEnabled, true);
  assert.equal(status.canManageManualPaymentInstructions, false);
  assert.equal(status.canManageProviderAuthorization, false);
  assert.deepEqual(status.providerAuthorizationActions, []);
  assert.equal(status.manualPaymentsOnly.statusLabel, "Manual Payments Only");
  assert.equal(status.providerVerificationUrl.available, false);
  assert.equal(
    status.individualCreatorPaymentPath.steps.some((step) =>
      /Public Trip URL/.test(step),
    ),
    true,
  );
});

test("Payment Setup status adapter normalizes Settlement Readiness blocker copy", () => {
  const status = normalizePaymentSetupStatus({
    online_payment_readiness_ready: false,
    online_payment_readiness_status_label: "Blocked",
    online_payment_readiness_blocker_code: "payout_account_not_ready",
    payout_status: "pending",
    payout_status_label: "Pending",
  });

  assert.equal(
    status.onlinePaymentReadinessBlockerCode,
    "settlement_readiness_not_ready",
  );
  assert.equal(
    status.onlinePaymentReadinessBlockerLabel,
    "Settlement Readiness not active",
  );
  assert.equal(status.settlementReadinessStatusLabel, "Pending");
});

test("Payment Setup status adapter normalizes backend payment methods", () => {
  const status = normalizePaymentSetupStatus({
    online_payment_readiness_ready: true,
    online_payment_readiness_status_label: "Ready",
    provider_payment_setup_complete: true,
    payment_method_readiness_ready: true,
    payment_method_readiness_status_label: "Ready",
    ready_payment_method_count: 1,
    ready_payment_method_ids: ["provider_payments"],
    payment_methods: [
      {
        id: "provider_payments",
        label: "Online payments",
        method_type: "provider_payment",
        ready: true,
        status_label: "Ready",
        blocker_code: "ready",
        blocker_label: "Ready",
        message: "Online payments are ready for public booking.",
        action_label: "Pay online",
        provider: "razorpay",
        provider_label: "Razorpay",
        online_payment_readiness_ready: true,
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
  });

  assert.equal(status.paymentMethodReadinessReady, true);
  assert.deepEqual(status.readyPaymentMethodIds, ["provider_payments"]);
  assert.equal(status.providerPaymentMethod.providerLabel, "Razorpay");
  assert.equal(status.manualPaymentMethod.ready, false);
  assert.equal(
    status.manualPaymentMethod.blockerLabel,
    "Manual Payment Instructions missing",
  );
});

test("Payment Setup status adapter normalizes Manual Payment Instructions readiness", () => {
  const status = normalizePaymentSetupStatus({
    manual_payment_instructions: {
      ready: true,
      status_label: "Ready",
      blocker_code: "ready",
      blocker_label: "Ready",
      message:
        "Manual Payment Instructions are ready for Trip-level Manual Payment Availability.",
      payment_qr_uploaded: true,
      payment_qr_url: "/media/payment-qr/organizer-7/payment-qr.png",
      original_filename: "payment-qr.png",
      content_type: "image/png",
      file_size: 512,
      upi_id: "trips@example",
      account_name: "Field Team Collective",
      bank_transfer_details: "Bank transfer details",
      can_manage: true,
      updated_at: "2026-05-29T01:30:00Z",
    },
    can_manage_manual_payment_instructions: true,
    manual_payment_method: {
      id: "qr_manual_payments",
      label: "Manual Payments",
      method_type: "qr_manual_payment",
      ready: false,
      status_label: "Blocked",
      blocker_code: "manual_payment_availability_closed",
      blocker_label: "Manual Payment Availability closed",
      message:
        "Manual Payments require open Manual Payment Availability for this Trip.",
      action_label: "Scan QR code to pay",
      manual_payment_instructions_ready: true,
      manual_payment_availability_open: false,
      requires_review: true,
    },
    provider_authorization_actions: [
      {
        id: "connect",
        label: "Connect with Razorpay",
        description:
          "Start OAuth Provider Authorization on Razorpay-hosted screens.",
        status_label: "Available",
        enabled: true,
        tone: "primary",
      },
    ],
  });

  assert.equal(status.manualPaymentInstructions.ready, true);
  assert.equal(status.manualPaymentInstructions.paymentQrUploaded, true);
  assert.equal(
    status.manualPaymentInstructions.paymentQrUrl,
    "http://localhost:8000/media/payment-qr/organizer-7/payment-qr.png",
  );
  assert.equal(status.manualPaymentInstructions.upiId, "trips@example");
  assert.equal(status.manualPaymentInstructions.canManage, true);
  assert.equal(status.canManageManualPaymentInstructions, true);
  assert.equal(status.manualPaymentMethod.manualPaymentInstructionsReady, true);
  assert.deepEqual(
    status.providerAuthorizationActions.map((action) => action.id),
    ["connect"],
  );
});

test("Payment Setup actions identify OAuth start actions", () => {
  assert.equal(providerAuthorizationActionKind("connect"), "start");
  assert.equal(providerAuthorizationActionKind("retry"), "start");
  assert.equal(providerAuthorizationActionKind("disconnect"), "unimplemented");
  assert.equal(paymentSetupActionKind("connect"), "start_authorization");
  assert.equal(paymentSetupActionKind("retry"), "start_authorization");
  assert.equal(paymentSetupActionKind("test_connection"), "test_connection");
  assert.equal(paymentSetupActionKind("replace"), "unimplemented");
});

test("Payment Setup adapter summarizes failed Provider Connection Tests", () => {
  const [result] = normalizeProviderConnectionTestResults([
    {
      id: 42,
      provider: "razorpay",
      provider_label: "Razorpay",
      provider_mode: "live",
      provider_mode_label: "Live",
      status: "failed",
      status_label: "Failed",
      provider_account_reference: "merchant_123",
      failure_reason: "provider_order_creation_failed",
      initiated_by_email: "owner@example.com",
      initiated_by_staff: false,
      started_at: "2026-05-29T02:50:00Z",
      completed_at: "2026-05-29T02:50:02Z",
      checks: {
        credentials: { status: "passed" },
        order_creation: { status: "failed" },
      },
    },
  ]);

  assert.equal(result?.status, "failed");
  assert.equal(result?.failureReason, "provider_order_creation_failed");
  assert.equal(result?.passedCheckCount, 1);
  assert.equal(result?.failedCheckCount, 1);
});
