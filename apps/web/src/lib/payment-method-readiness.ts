export type PaymentMethodReadiness = {
  id: string;
  label: string;
  methodType: string;
  ready: boolean;
  statusLabel: string;
  blockerCode: string;
  blockerLabel: string;
  message: string;
  actionLabel: string;
  provider: string;
  providerLabel: string;
  onlinePaymentReadinessReady: boolean | null;
  manualPaymentInstructionsReady: boolean | null;
  manualPaymentAvailabilityOpen: boolean | null;
  requiresReview: boolean;
};

export type PaymentMethodReadinessSummary = {
  ready: boolean;
  statusLabel: string;
  readyMethodCount: number;
  readyMethodIds: string[];
  methods: PaymentMethodReadiness[];
  providerPaymentMethod: PaymentMethodReadiness;
  manualPaymentMethod: PaymentMethodReadiness;
};

export type PaymentMethodReadinessApiPayload = {
  payment_method_readiness_ready?: boolean;
  payment_method_readiness_status_label?: string;
  ready_payment_method_count?: number;
  ready_payment_method_ids?: unknown[];
  payment_methods?: PaymentMethodReadinessMethodApiPayload[];
  provider_payment_method?: PaymentMethodReadinessMethodApiPayload;
  manual_payment_method?: PaymentMethodReadinessMethodApiPayload;
  online_payment_readiness_ready?: boolean;
  online_payment_readiness_status_label?: string;
  online_payment_readiness_message?: string;
  provider_payment_setup_complete?: boolean;
};

export type PaymentMethodReadinessMethodApiPayload = {
  id?: string;
  label?: string;
  method_type?: string;
  ready?: boolean;
  status_label?: string;
  blocker_code?: string;
  blocker_label?: string;
  message?: string;
  action_label?: string;
  provider?: string;
  provider_label?: string;
  online_payment_readiness_ready?: boolean | null;
  manual_payment_instructions_ready?: boolean | null;
  manual_payment_availability_open?: boolean | null;
  requires_review?: boolean;
};

export function normalizePaymentMethodReadiness(
  payload?: PaymentMethodReadinessApiPayload | null,
): PaymentMethodReadinessSummary {
  const providerPaymentMethod = normalizePaymentMethod(
    payload?.provider_payment_method,
    fallbackProviderPaymentMethod(payload),
  );
  const manualPaymentMethod = normalizePaymentMethod(
    payload?.manual_payment_method,
    fallbackManualPaymentMethod(),
  );
  const explicitMethods = payload?.payment_methods
    ?.map((method) => normalizePaymentMethod(method))
    .filter((method) => method.id);
  const methods = explicitMethods?.length
    ? ensureKnownMethods(explicitMethods, providerPaymentMethod, manualPaymentMethod)
    : [providerPaymentMethod, manualPaymentMethod];
  const readyMethodIds =
    payload?.ready_payment_method_ids
      ?.filter((id): id is string => typeof id === "string") ??
    methods.filter((method) => method.ready).map((method) => method.id);
  const ready =
    payload?.payment_method_readiness_ready ??
    methods.some((method) => method.ready);

  return {
    ready,
    statusLabel:
      payload?.payment_method_readiness_status_label ??
      (ready ? "Ready" : "Blocked"),
    readyMethodCount:
      payload?.ready_payment_method_count ?? readyMethodIds.length,
    readyMethodIds,
    methods,
    providerPaymentMethod:
      methods.find((method) => method.id === "provider_payments") ??
      providerPaymentMethod,
    manualPaymentMethod:
      methods.find((method) => method.id === "qr_manual_payments") ??
      manualPaymentMethod,
  };
}

function normalizePaymentMethod(
  payload?: PaymentMethodReadinessMethodApiPayload | null,
  fallback?: PaymentMethodReadinessMethodApiPayload,
): PaymentMethodReadiness {
  const source = { ...fallback, ...payload };
  const ready = source.ready ?? false;
  return {
    id: source.id ?? "",
    label: source.label ?? "Payment method",
    methodType: source.method_type ?? "",
    ready,
    statusLabel: source.status_label ?? (ready ? "Ready" : "Blocked"),
    blockerCode: source.blocker_code ?? (ready ? "ready" : "blocked"),
    blockerLabel: source.blocker_label ?? (ready ? "Ready" : "Blocked"),
    message: source.message ?? "Payment method status is unavailable.",
    actionLabel: source.action_label ?? "",
    provider: source.provider ?? "",
    providerLabel: source.provider_label ?? "",
    onlinePaymentReadinessReady:
      source.online_payment_readiness_ready ?? null,
    manualPaymentInstructionsReady:
      source.manual_payment_instructions_ready ?? null,
    manualPaymentAvailabilityOpen:
      source.manual_payment_availability_open ?? null,
    requiresReview: source.requires_review ?? false,
  };
}

function fallbackProviderPaymentMethod(
  payload?: PaymentMethodReadinessApiPayload | null,
): PaymentMethodReadinessMethodApiPayload {
  const ready =
    payload?.online_payment_readiness_ready ??
    payload?.provider_payment_setup_complete ??
    false;
  return {
    id: "provider_payments",
    label: "Online payments",
    method_type: "provider_payment",
    ready,
    status_label:
      payload?.online_payment_readiness_status_label ??
      (ready ? "Ready" : "Blocked"),
    blocker_code: ready ? "ready" : "online_payment_readiness_blocked",
    blocker_label: ready ? "Ready" : "Online Payment Readiness blocked",
    message:
      payload?.online_payment_readiness_message ??
      (ready
        ? "Online payments are ready for public booking."
        : "Online Payment Readiness is blocked."),
    action_label: "Pay online",
    provider: "razorpay",
    provider_label: "Razorpay",
    online_payment_readiness_ready: ready,
    requires_review: false,
  };
}

function fallbackManualPaymentMethod(): PaymentMethodReadinessMethodApiPayload {
  return {
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
  };
}

function ensureKnownMethods(
  methods: PaymentMethodReadiness[],
  providerPaymentMethod: PaymentMethodReadiness,
  manualPaymentMethod: PaymentMethodReadiness,
): PaymentMethodReadiness[] {
  const ids = new Set(methods.map((method) => method.id));
  return [
    ...methods,
    ...(ids.has("provider_payments") ? [] : [providerPaymentMethod]),
    ...(ids.has("qr_manual_payments") ? [] : [manualPaymentMethod]),
  ];
}
