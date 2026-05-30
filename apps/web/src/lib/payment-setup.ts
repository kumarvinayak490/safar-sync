import {
  authenticatedServerJsonRequest,
  drfApiUrl,
  extractDrfErrorMessage,
  multipartFormRequest,
} from "./drf-request.ts";
import {
  normalizePaymentMethodReadiness,
  type PaymentMethodReadiness,
  type PaymentMethodReadinessApiPayload,
} from "./payment-method-readiness.ts";

export type PaymentSetupStatus = {
  provider: string;
  providerLabel: string;
  providerDisclosure: string;
  payoutStatus: string;
  payoutStatusLabel: string;
  settlementReadinessStatus: string;
  settlementReadinessStatusLabel: string;
  settlementReadinessReady: boolean;
  providerPaymentSetupStatus: string;
  providerPaymentSetupStatusLabel: string;
  providerPaymentSetupComplete: boolean;
  providerAuthorizationMethod: string;
  providerAuthorizationMethodLabel: string;
  providerAuthorizationState: string;
  providerAuthorizationStateLabel: string;
  onlinePaymentReadinessReady: boolean;
  onlinePaymentReadinessStatusLabel: string;
  onlinePaymentReadinessBlockerCode: string;
  onlinePaymentReadinessBlockerLabel: string;
  onlinePaymentReadinessMessage: string;
  paymentMethodReadinessReady: boolean;
  paymentMethodReadinessStatusLabel: string;
  readyPaymentMethodCount: number;
  readyPaymentMethodIds: string[];
  paymentMethods: PaymentMethodReadiness[];
  providerPaymentMethod: PaymentMethodReadiness;
  manualPaymentMethod: PaymentMethodReadiness;
  providerVerificationStatus: string;
  providerVerificationStatusLabel: string;
  payoutAccountReady: boolean;
  providerPaymentCapabilityEnabled: boolean;
  providerConnectionState: string;
  providerConnectionStateLabel: string;
  providerMode: string;
  providerModeLabel: string;
  providerOrderCreationAvailable: boolean;
  manualPaymentCapabilityEnabled: boolean;
  canManageManualPaymentInstructions: boolean;
  manualPaymentInstructions: ManualPaymentInstructions;
  canManageProviderAuthorization: boolean;
  paymentSetupAccessMessage: string;
  providerAuthorizationActions: PaymentSetupActionDescriptor[];
  individualCreatorPaymentPath: IndividualCreatorPaymentPath;
  providerVerificationUrl: ProviderVerificationUrl;
  manualPaymentsOnly: ManualPaymentsOnlyFallback;
};

export type ProviderConnectionTestResult = {
  id: number;
  provider: string;
  providerLabel: string;
  providerMode: string;
  providerModeLabel: string;
  status: string;
  statusLabel: string;
  providerAccountReference: string;
  failureReason: string;
  initiatedByEmail: string;
  initiatedByStaff: boolean;
  startedAt: string;
  completedAt: string;
  passedCheckCount: number;
  failedCheckCount: number;
  skippedCheckCount: number;
};

export type ManualPaymentInstructions = {
  ready: boolean;
  statusLabel: string;
  blockerCode: string;
  blockerLabel: string;
  message: string;
  paymentQrUploaded: boolean;
  paymentQrUrl: string;
  originalFilename: string;
  contentType: string;
  fileSize: number;
  upiId: string;
  accountName: string;
  bankTransferDetails: string;
  canManage: boolean;
  updatedAt: string;
};

export type PaymentSetupActionDescriptor = {
  id:
    | "connect"
    | "retry"
    | "disconnect"
    | "replace"
    | "test_connection"
    | string;
  label: string;
  description: string;
  statusLabel: string;
  enabled: boolean;
  tone: "primary" | "secondary" | "danger" | string;
};

export type IndividualCreatorPaymentPath = {
  title: string;
  summary: string;
  steps: string[];
};

export type ProviderVerificationUrl = {
  available: boolean;
  source: string;
  sourceLabel: string;
  urlPath: string;
  tripId: number | null;
  tripTitle: string;
  statusLabel: string;
  message: string;
};

export type ManualPaymentsOnlyFallback = {
  supported: boolean;
  active: boolean;
  statusLabel: string;
  publicBookingMessage: string;
  manualOperationsMessage: string;
};

export type OrganizerPaymentSetup = {
  status: PaymentSetupStatus;
  providerConnectionTests: ProviderConnectionTestResult[];
  payoutAccount: {
    holderName: string;
    providerAccountReference: string;
    status: string;
    statusLabel: string;
    notes: string;
    updatedAt: string;
  };
  providerPaymentSetup: {
    provider: string;
    providerLabel: string;
    providerDisclosure: string;
    status: string;
    statusLabel: string;
    providerMerchantReference: string;
    authorizationMethod: string;
    authorizationMethodLabel: string;
    authorizationState: string;
    authorizationStateLabel: string;
    providerVerificationStatus: string;
    providerVerificationStatusLabel: string;
    providerPaymentCapabilityEnabled: boolean;
    providerConnectionState: string;
    providerConnectionStateLabel: string;
    providerMode: string;
    providerModeLabel: string;
    isComplete: boolean;
    updatedAt: string;
  };
};

export type ProviderAuthorizationStartResult =
  | {
      ok: true;
      authorizationUrl: string;
    }
  | {
      ok: false;
      message: string;
    };

export type ProviderConnectionTestRunResult =
  | {
      ok: true;
      result: ProviderConnectionTestResult;
    }
  | {
      ok: false;
      message: string;
    };

export async function getOrganizerPaymentSetup(
  organizerId: number,
): Promise<OrganizerPaymentSetup | null> {
  const [statusResult, payoutResult, providerResult, testsResult] =
    await Promise.all([
      authenticatedServerJsonRequest<PaymentSetupStatusApiPayload>(
        `/api/organizers/${organizerId}/payment-setup-status/`,
      ),
      authenticatedServerJsonRequest<PayoutAccountApiPayload>(
        `/api/organizers/${organizerId}/payout-account/`,
      ),
      authenticatedServerJsonRequest<ProviderPaymentSetupApiPayload>(
        `/api/organizers/${organizerId}/provider-payment-setup/`,
      ),
      authenticatedServerJsonRequest<ProviderConnectionTestResultApiPayload[]>(
        `/api/organizers/${organizerId}/provider-connection-tests/`,
      ),
    ]);

  if (
    !statusResult.response.ok ||
    !statusResult.data ||
    !payoutResult.response.ok ||
    !payoutResult.data ||
    !providerResult.response.ok ||
    !providerResult.data
  ) {
    return null;
  }

  return normalizeOrganizerPaymentSetup({
    status: statusResult.data,
    payoutAccount: payoutResult.data,
    providerPaymentSetup: providerResult.data,
    providerConnectionTests: testsResult.response.ok ? testsResult.data : [],
  });
}

export async function getProviderConnectionTests(
  organizerId: number,
): Promise<ProviderConnectionTestResult[]> {
  try {
    const result = await authenticatedServerJsonRequest<
      ProviderConnectionTestResultApiPayload[]
    >(`/api/organizers/${organizerId}/provider-connection-tests/`);

    if (!result.response.ok || !result.data) {
      return [];
    }

    return normalizeProviderConnectionTestResults(result.data);
  } catch {
    return [];
  }
}

export async function startProviderAuthorization(
  organizerId: number,
  providerMode: string,
): Promise<ProviderAuthorizationStartResult> {
  try {
    const result =
      await authenticatedServerJsonRequest<ProviderAuthorizationStartApiPayload>(
        `/api/organizers/${organizerId}/provider-authorization/start/`,
        {
          method: "POST",
          csrf: true,
          body: {
            provider_mode: providerMode,
          },
        },
      );

    if (!result.response.ok || !result.data?.authorization_url) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, [
            "provider_mode",
            "provider",
            "detail",
            "non_field_errors",
          ]) ?? "Provider Authorization could not be started.",
      };
    }

    return {
      ok: true,
      authorizationUrl: result.data.authorization_url,
    };
  } catch {
    return {
      ok: false,
      message:
        "TripOS could not reach Provider Authorization. Try again after the API is running.",
    };
  }
}

export async function runProviderConnectionTest(
  organizerId: number,
): Promise<ProviderConnectionTestRunResult> {
  try {
    const result =
      await authenticatedServerJsonRequest<ProviderConnectionTestResultApiPayload>(
        `/api/organizers/${organizerId}/provider-connection-tests/`,
        {
          method: "POST",
          csrf: true,
          body: {},
        },
      );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, [
            "provider_connection_test",
            "credentials",
            "detail",
            "non_field_errors",
          ]) ?? "Provider Connection Test could not run.",
      };
    }

    return {
      ok: true,
      result: normalizeProviderConnectionTestResult(result.data),
    };
  } catch {
    return {
      ok: false,
      message:
        "TripOS could not reach Provider Connection Test. Try again after the API is running.",
    };
  }
}

export async function updateManualPaymentInstructions(
  organizerId: number,
  formData: FormData,
): Promise<
  | { ok: true; instructions: ManualPaymentInstructions }
  | { ok: false; message: string }
> {
  try {
    const result =
      await multipartFormRequest<ManualPaymentInstructionsApiPayload>(
        `/api/organizers/${organizerId}/manual-payment-instructions/`,
        {
          method: "PATCH",
          csrf: true,
          authenticated: true,
          formData,
        },
      );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, [
            "payment_qr",
            "upi_id",
            "account_name",
            "bank_transfer_details",
            "non_field_errors",
            "detail",
          ]) ?? "Manual Payment Instructions could not be saved.",
      };
    }

    return {
      ok: true,
      instructions: normalizeManualPaymentInstructions(result.data),
    };
  } catch {
    return {
      ok: false,
      message:
        "TripOS could not reach Manual Payment Instructions. Try again after the API is running.",
    };
  }
}

export async function removeManualPaymentInstructions(
  organizerId: number,
): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    const result = await authenticatedServerJsonRequest<null>(
      `/api/organizers/${organizerId}/manual-payment-instructions/`,
      {
        method: "DELETE",
        csrf: true,
      },
    );

    if (!result.response.ok) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, ["detail"]) ??
          "Manual Payment Instructions could not be removed.",
      };
    }

    return { ok: true };
  } catch {
    return {
      ok: false,
      message:
        "TripOS could not reach Manual Payment Instructions. Try again after the API is running.",
    };
  }
}

export function providerAuthorizationActionKind(
  actionId: string,
): "start" | "unimplemented" {
  return actionId === "connect" || actionId === "retry"
    ? "start"
    : "unimplemented";
}

export function paymentSetupActionKind(
  actionId: string,
): "start_authorization" | "test_connection" | "unimplemented" {
  if (actionId === "connect" || actionId === "retry") {
    return "start_authorization";
  }
  if (actionId === "test_connection") {
    return "test_connection";
  }
  return "unimplemented";
}

export function normalizePaymentSetupStatus(
  payload?: PaymentSetupStatusApiPayload | null,
): PaymentSetupStatus {
  const providerPaymentSetupComplete =
    payload?.provider_payment_setup_complete ?? false;
  const paymentMethodReadiness = normalizePaymentMethodReadiness(payload);
  const blockerCode = normalizeReadinessBlockerCode(
    payload?.online_payment_readiness_blocker_code ??
      (providerPaymentSetupComplete
        ? "ready"
        : "provider_verification_not_verified"),
  );

  return {
    provider: payload?.provider ?? "razorpay",
    providerLabel: payload?.provider_label ?? "Razorpay",
    providerDisclosure:
      payload?.provider_disclosure ??
      "Razorpay processes provider-confirmed payments and provider verification for the India MVP.",
    payoutStatus: payload?.payout_status ?? "not_started",
    payoutStatusLabel: payload?.payout_status_label ?? "Not started",
    settlementReadinessStatus:
      payload?.settlement_readiness_status ??
      payload?.payout_status ??
      "not_started",
    settlementReadinessStatusLabel:
      payload?.settlement_readiness_status_label ??
      payload?.payout_status_label ??
      "Not started",
    settlementReadinessReady:
      payload?.settlement_readiness_ready ??
      payload?.payout_account_ready ??
      false,
    providerPaymentSetupStatus:
      payload?.provider_payment_setup_status ?? "not_started",
    providerPaymentSetupStatusLabel:
      payload?.provider_payment_setup_status_label ?? "Not started",
    providerPaymentSetupComplete,
    providerAuthorizationMethod:
      payload?.provider_authorization_method ?? "oauth",
    providerAuthorizationMethodLabel:
      payload?.provider_authorization_method_label ??
      "OAuth Provider Authorization",
    providerAuthorizationState:
      payload?.provider_authorization_state ?? "not_started",
    providerAuthorizationStateLabel:
      payload?.provider_authorization_state_label ?? "Not started",
    onlinePaymentReadinessReady:
      payload?.online_payment_readiness_ready ??
      payload?.provider_payment_setup_complete ??
      false,
    onlinePaymentReadinessStatusLabel:
      payload?.online_payment_readiness_status_label ??
      (providerPaymentSetupComplete ? "Ready" : "Blocked"),
    onlinePaymentReadinessBlockerCode: blockerCode,
    onlinePaymentReadinessBlockerLabel:
      payload?.online_payment_readiness_blocker_label ??
      readinessBlockerLabel(blockerCode),
    onlinePaymentReadinessMessage:
      payload?.online_payment_readiness_message ??
      (providerPaymentSetupComplete
        ? "Online Payment Readiness is ready for public booking."
        : "Online Payment Readiness is blocked."),
    paymentMethodReadinessReady: paymentMethodReadiness.ready,
    paymentMethodReadinessStatusLabel: paymentMethodReadiness.statusLabel,
    readyPaymentMethodCount: paymentMethodReadiness.readyMethodCount,
    readyPaymentMethodIds: paymentMethodReadiness.readyMethodIds,
    paymentMethods: paymentMethodReadiness.methods,
    providerPaymentMethod: paymentMethodReadiness.providerPaymentMethod,
    manualPaymentMethod: paymentMethodReadiness.manualPaymentMethod,
    providerVerificationStatus:
      payload?.provider_verification_status ?? "not_started",
    providerVerificationStatusLabel:
      payload?.provider_verification_status_label ?? "Not started",
    payoutAccountReady: payload?.payout_account_ready ?? false,
    providerPaymentCapabilityEnabled:
      payload?.provider_payment_capability_enabled ?? false,
    providerConnectionState: payload?.provider_connection_state ?? "unhealthy",
    providerConnectionStateLabel:
      payload?.provider_connection_state_label ?? "Unhealthy",
    providerMode: payload?.provider_mode ?? "test",
    providerModeLabel: payload?.provider_mode_label ?? "Test",
    providerOrderCreationAvailable:
      payload?.provider_order_creation_available ?? false,
    manualPaymentCapabilityEnabled:
      payload?.manual_payment_capability_enabled ?? true,
    canManageManualPaymentInstructions:
      payload?.can_manage_manual_payment_instructions ?? false,
    manualPaymentInstructions: normalizeManualPaymentInstructions(
      payload?.manual_payment_instructions,
    ),
    canManageProviderAuthorization:
      payload?.can_manage_provider_authorization ?? false,
    paymentSetupAccessMessage:
      payload?.payment_setup_access_message ??
      "Operators can view readiness blockers and recovery context, but only Owners can manage Provider Authorization.",
    providerAuthorizationActions: normalizePaymentSetupActions(
      payload?.provider_authorization_actions,
    ),
    individualCreatorPaymentPath: normalizeIndividualCreatorPaymentPath(
      payload?.individual_creator_payment_path,
    ),
    providerVerificationUrl: normalizeProviderVerificationUrl(
      payload?.provider_verification_url,
    ),
    manualPaymentsOnly: normalizeManualPaymentsOnly(
      payload?.manual_payments_only,
    ),
  };
}

function normalizeReadinessBlockerCode(code: string): string {
  if (code === "payout_account_not_ready") {
    return "settlement_readiness_not_ready";
  }
  return code;
}

function readinessBlockerLabel(code: string): string {
  switch (code) {
    case "ready":
      return "Ready";
    case "settlement_readiness_not_ready":
      return "Settlement Readiness not active";
    case "provider_payment_capability_disabled":
      return "Provider payment capability disabled";
    case "provider_connection_unhealthy":
      return "Provider connection unhealthy";
    case "provider_mode_not_live":
      return "Provider mode not live";
    case "provider_verification_not_verified":
    default:
      return "Provider verification not verified";
  }
}

function normalizePaymentSetupActions(
  payload?: PaymentSetupActionApiPayload[] | null,
): PaymentSetupActionDescriptor[] {
  return (
    payload
      ?.filter((action) => typeof action?.id === "string")
      .map((action) => ({
        id: action.id ?? "connect",
        label: action.label ?? "Payment Setup action",
        description:
          action.description ??
          "Manage Provider Authorization for the connected provider account.",
        statusLabel: action.status_label ?? "Available",
        enabled: action.enabled ?? false,
        tone: action.tone ?? "secondary",
      })) ?? []
  );
}

function normalizeIndividualCreatorPaymentPath(
  payload?: IndividualCreatorPaymentPathApiPayload | null,
): IndividualCreatorPaymentPath {
  return {
    title: payload?.title ?? "Individual Creator Payment Path",
    summary:
      payload?.summary ??
      "Creator-led Organizers can connect a provider account that matches how they already collect trip payments.",
    steps: payload?.steps?.filter(
      (step): step is string => typeof step === "string",
    ) ?? [
      "Publish a Public Trip Page before submitting provider verification.",
      "Use the TripOS Public Trip URL to show where travelers will pay.",
      "Complete provider-hosted verification and payout steps outside TripOS.",
    ],
  };
}

function normalizeProviderVerificationUrl(
  payload?: ProviderVerificationUrlApiPayload | null,
): ProviderVerificationUrl {
  return {
    available: payload?.available ?? false,
    source: payload?.source ?? "public_trip_url",
    sourceLabel: payload?.source_label ?? "TripOS Public Trip URL",
    urlPath: payload?.url_path ?? "",
    tripId: payload?.trip_id ?? null,
    tripTitle: payload?.trip_title ?? "",
    statusLabel: payload?.status_label ?? "Publish a Public Trip Page",
    message:
      payload?.message ??
      "Publish a Public Trip Page from Launch, then use that TripOS URL as the Provider Verification URL.",
  };
}

function normalizeManualPaymentsOnly(
  payload?: ManualPaymentsOnlyApiPayload | null,
): ManualPaymentsOnlyFallback {
  return {
    supported: payload?.supported ?? true,
    active: payload?.active ?? true,
    statusLabel: payload?.status_label ?? "Manual Payments Only",
    publicBookingMessage:
      payload?.public_booking_message ??
      "Public Booking stays closed with Bookings Opening Soon until Online Payment Readiness is ready.",
    manualOperationsMessage:
      payload?.manual_operations_message ??
      "Manual Bookings and Manual Payments remain available in the Operations Dashboard.",
  };
}

export function normalizeManualPaymentInstructions(
  payload?: ManualPaymentInstructionsApiPayload | null,
): ManualPaymentInstructions {
  const ready = payload?.ready ?? false;
  return {
    ready,
    statusLabel:
      payload?.status_label ?? (ready ? "Ready" : "Missing Payment QR"),
    blockerCode:
      payload?.blocker_code ?? (ready ? "ready" : "payment_qr_missing"),
    blockerLabel:
      payload?.blocker_label ?? (ready ? "Ready" : "Payment QR missing"),
    message:
      payload?.message ??
      "Manual Payment Instructions need a Payment QR before Manual Payments can be offered from Launch.",
    paymentQrUploaded: payload?.payment_qr_uploaded ?? false,
    paymentQrUrl: normalizePaymentSetupAssetUrl(payload?.payment_qr_url ?? ""),
    originalFilename: payload?.original_filename ?? "",
    contentType: payload?.content_type ?? "",
    fileSize: payload?.file_size ?? 0,
    upiId: payload?.upi_id ?? "",
    accountName: payload?.account_name ?? "",
    bankTransferDetails: payload?.bank_transfer_details ?? "",
    canManage: payload?.can_manage ?? false,
    updatedAt: payload?.updated_at ?? "",
  };
}

function normalizePaymentSetupAssetUrl(url: string): string {
  if (!url) {
    return "";
  }

  if (/^https?:\/\//i.test(url)) {
    return url;
  }

  return drfApiUrl(url.startsWith("/") ? url : `/${url}`);
}

export function normalizeOrganizerPaymentSetup({
  payoutAccount,
  providerConnectionTests,
  providerPaymentSetup,
  status,
}: {
  status?: PaymentSetupStatusApiPayload | null;
  payoutAccount?: PayoutAccountApiPayload | null;
  providerPaymentSetup?: ProviderPaymentSetupApiPayload | null;
  providerConnectionTests?: ProviderConnectionTestResultApiPayload[] | null;
}): OrganizerPaymentSetup {
  return {
    status: normalizePaymentSetupStatus(status),
    providerConnectionTests: normalizeProviderConnectionTestResults(
      providerConnectionTests,
    ),
    payoutAccount: {
      holderName: payoutAccount?.holder_name ?? "",
      providerAccountReference: payoutAccount?.provider_account_reference ?? "",
      status: payoutAccount?.status ?? "not_started",
      statusLabel: payoutAccount?.status_label ?? "Not started",
      notes: payoutAccount?.notes ?? "",
      updatedAt: payoutAccount?.updated_at ?? "",
    },
    providerPaymentSetup: {
      provider:
        providerPaymentSetup?.provider ?? status?.provider ?? "razorpay",
      providerLabel:
        providerPaymentSetup?.provider_label ??
        status?.provider_label ??
        "Razorpay",
      providerDisclosure:
        providerPaymentSetup?.provider_disclosure ??
        status?.provider_disclosure ??
        "Razorpay processes provider-confirmed payments and provider verification for the India MVP.",
      status: providerPaymentSetup?.status ?? "not_started",
      statusLabel: providerPaymentSetup?.status_label ?? "Not started",
      providerMerchantReference:
        providerPaymentSetup?.provider_merchant_reference ?? "",
      authorizationMethod:
        providerPaymentSetup?.authorization_method ??
        status?.provider_authorization_method ??
        "oauth",
      authorizationMethodLabel:
        providerPaymentSetup?.authorization_method_label ??
        status?.provider_authorization_method_label ??
        "OAuth Provider Authorization",
      authorizationState:
        providerPaymentSetup?.authorization_state ??
        status?.provider_authorization_state ??
        "not_started",
      authorizationStateLabel:
        providerPaymentSetup?.authorization_state_label ??
        status?.provider_authorization_state_label ??
        "Not started",
      providerVerificationStatus:
        providerPaymentSetup?.provider_verification_status ??
        status?.provider_verification_status ??
        "not_started",
      providerVerificationStatusLabel:
        providerPaymentSetup?.provider_verification_status_label ??
        status?.provider_verification_status_label ??
        "Not started",
      providerPaymentCapabilityEnabled:
        providerPaymentSetup?.provider_payment_capability_enabled ??
        status?.provider_payment_capability_enabled ??
        false,
      providerConnectionState:
        providerPaymentSetup?.provider_connection_state ??
        status?.provider_connection_state ??
        "unhealthy",
      providerConnectionStateLabel:
        providerPaymentSetup?.provider_connection_state_label ??
        status?.provider_connection_state_label ??
        "Unhealthy",
      providerMode:
        providerPaymentSetup?.provider_mode ?? status?.provider_mode ?? "test",
      providerModeLabel:
        providerPaymentSetup?.provider_mode_label ??
        status?.provider_mode_label ??
        "Test",
      isComplete:
        providerPaymentSetup?.is_complete ??
        status?.provider_payment_setup_complete ??
        false,
      updatedAt: providerPaymentSetup?.updated_at ?? "",
    },
  };
}

export function normalizeProviderConnectionTestResults(
  payload?: ProviderConnectionTestResultApiPayload[] | null,
): ProviderConnectionTestResult[] {
  return (
    payload
      ?.filter((result) => typeof result?.id === "number")
      .map(normalizeProviderConnectionTestResult) ?? []
  );
}

export function normalizeProviderConnectionTestResult(
  payload?: ProviderConnectionTestResultApiPayload | null,
): ProviderConnectionTestResult {
  const checks = payload?.checks ?? {};
  let passedCheckCount = 0;
  let failedCheckCount = 0;
  let skippedCheckCount = 0;
  for (const check of Object.values(checks)) {
    if (!check || typeof check !== "object") {
      continue;
    }
    const status = (check as { status?: unknown }).status;
    if (status === "passed") {
      passedCheckCount += 1;
    } else if (status === "failed") {
      failedCheckCount += 1;
    } else if (status === "skipped") {
      skippedCheckCount += 1;
    }
  }

  return {
    id: payload?.id ?? 0,
    provider: payload?.provider ?? "razorpay",
    providerLabel: payload?.provider_label ?? "Razorpay",
    providerMode: payload?.provider_mode ?? "test",
    providerModeLabel: payload?.provider_mode_label ?? "Test",
    status: payload?.status ?? "failed",
    statusLabel: payload?.status_label ?? "Failed",
    providerAccountReference: payload?.provider_account_reference ?? "",
    failureReason: payload?.failure_reason ?? "",
    initiatedByEmail: payload?.initiated_by_email ?? "",
    initiatedByStaff: payload?.initiated_by_staff ?? false,
    startedAt: payload?.started_at ?? "",
    completedAt: payload?.completed_at ?? "",
    passedCheckCount,
    failedCheckCount,
    skippedCheckCount,
  };
}

export type PaymentSetupStatusApiPayload = PaymentMethodReadinessApiPayload & {
  provider?: string;
  provider_label?: string;
  provider_disclosure?: string;
  payout_status?: string;
  payout_status_label?: string;
  settlement_readiness_status?: string;
  settlement_readiness_status_label?: string;
  settlement_readiness_ready?: boolean;
  provider_payment_setup_status?: string;
  provider_payment_setup_status_label?: string;
  provider_payment_setup_complete?: boolean;
  provider_authorization_method?: string;
  provider_authorization_method_label?: string;
  provider_authorization_state?: string;
  provider_authorization_state_label?: string;
  online_payment_readiness_ready?: boolean;
  online_payment_readiness_status_label?: string;
  online_payment_readiness_blocker_code?: string;
  online_payment_readiness_blocker_label?: string;
  online_payment_readiness_message?: string;
  provider_verification_status?: string;
  provider_verification_status_label?: string;
  payout_account_ready?: boolean;
  provider_payment_capability_enabled?: boolean;
  provider_connection_state?: string;
  provider_connection_state_label?: string;
  provider_mode?: string;
  provider_mode_label?: string;
  provider_order_creation_available?: boolean;
  manual_payment_capability_enabled?: boolean;
  can_manage_manual_payment_instructions?: boolean;
  manual_payment_instructions?: ManualPaymentInstructionsApiPayload;
  can_manage_provider_authorization?: boolean;
  payment_setup_access_message?: string;
  provider_authorization_actions?: PaymentSetupActionApiPayload[];
  individual_creator_payment_path?: IndividualCreatorPaymentPathApiPayload;
  provider_verification_url?: ProviderVerificationUrlApiPayload;
  manual_payments_only?: ManualPaymentsOnlyApiPayload;
};

type PaymentSetupActionApiPayload = {
  id?: string;
  label?: string;
  description?: string;
  status_label?: string;
  enabled?: boolean;
  tone?: string;
};

type ProviderAuthorizationStartApiPayload = {
  provider?: string;
  provider_mode?: string;
  authorization_url?: string;
  state?: string;
  expires_at?: string;
  payment_setup?: PaymentSetupStatusApiPayload;
};

type IndividualCreatorPaymentPathApiPayload = {
  title?: string;
  summary?: string;
  steps?: unknown[];
};

type ProviderVerificationUrlApiPayload = {
  available?: boolean;
  source?: string;
  source_label?: string;
  url_path?: string;
  trip_id?: number | null;
  trip_title?: string;
  status_label?: string;
  message?: string;
};

type ManualPaymentsOnlyApiPayload = {
  supported?: boolean;
  active?: boolean;
  status_label?: string;
  public_booking_message?: string;
  manual_operations_message?: string;
};

export type ManualPaymentInstructionsApiPayload = {
  ready?: boolean;
  status_label?: string;
  blocker_code?: string;
  blocker_label?: string;
  message?: string;
  payment_qr_uploaded?: boolean;
  payment_qr_url?: string;
  original_filename?: string;
  content_type?: string;
  file_size?: number;
  upi_id?: string;
  account_name?: string;
  bank_transfer_details?: string;
  can_manage?: boolean;
  updated_at?: string;
};

export type PayoutAccountApiPayload = {
  holder_name?: string;
  provider_account_reference?: string;
  status?: string;
  status_label?: string;
  notes?: string;
  updated_at?: string;
};

export type ProviderPaymentSetupApiPayload = {
  provider?: string;
  provider_label?: string;
  provider_disclosure?: string;
  status?: string;
  status_label?: string;
  provider_merchant_reference?: string;
  authorization_method?: string;
  authorization_method_label?: string;
  authorization_state?: string;
  authorization_state_label?: string;
  provider_verification_status?: string;
  provider_verification_status_label?: string;
  provider_payment_capability_enabled?: boolean;
  provider_connection_state?: string;
  provider_connection_state_label?: string;
  provider_mode?: string;
  provider_mode_label?: string;
  is_complete?: boolean;
  updated_at?: string;
};

export type ProviderConnectionTestResultApiPayload = {
  id?: number;
  provider?: string;
  provider_label?: string;
  provider_mode?: string;
  provider_mode_label?: string;
  status?: string;
  status_label?: string;
  provider_account_reference?: string;
  checks?: Record<string, unknown>;
  failure_reason?: string;
  initiated_by_email?: string;
  initiated_by_staff?: boolean;
  started_at?: string;
  completed_at?: string;
};
