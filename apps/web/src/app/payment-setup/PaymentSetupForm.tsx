"use client";

import {
  Activity,
  ArrowLeftRight,
  Banknote,
  CircleOff,
  Plug,
  QrCode,
  RefreshCcw,
  Trash2,
  Unplug,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { useFormState, useFormStatus } from "react-dom";

import type {
  ManualPaymentInstructionsActionState,
  ProviderAuthorizationActionState,
  ProviderConnectionTestActionState,
} from "@/app/payment-setup/actions";
import {
  paymentSetupActionKind,
  providerAuthorizationActionKind,
} from "@/lib/payment-setup";
import type {
  ManualPaymentInstructions,
  PaymentSetupActionDescriptor,
  PaymentSetupStatus,
  ProviderConnectionTestResult,
} from "@/lib/payment-setup";

type PaymentSetupActionSurfaceProps = {
  startAuthorizationAction: (
    previousState: ProviderAuthorizationActionState,
    formData: FormData,
  ) => Promise<ProviderAuthorizationActionState>;
  canManage: boolean;
  hidePrimaryAuthorization?: boolean;
  organizerId: number;
  providerConnectionTests?: ProviderConnectionTestResult[];
  runProviderConnectionTestAction: (
    previousState: ProviderConnectionTestActionState,
    formData: FormData,
  ) => Promise<ProviderConnectionTestActionState>;
  status: PaymentSetupStatus;
};

type PaymentSetupFact = {
  label: string;
  value: string;
  detail: string;
  clear: boolean;
};

const actionIcons: Record<string, LucideIcon> = {
  connect: Plug,
  retry: RefreshCcw,
  disconnect: Unplug,
  replace: ArrowLeftRight,
  test_connection: Activity,
};

const initialProviderAuthorizationState: ProviderAuthorizationActionState = {
  error: "",
};

const initialProviderConnectionTestState: ProviderConnectionTestActionState = {
  error: "",
  message: "",
};

const initialManualPaymentInstructionsState: ManualPaymentInstructionsActionState =
  {
    error: "",
    message: "",
  };

type ManualPaymentInstructionsPanelProps = {
  canManage: boolean;
  instructions: ManualPaymentInstructions;
  organizerId: number;
  removeManualPaymentInstructionsAction: (
    previousState: ManualPaymentInstructionsActionState,
    formData: FormData,
  ) => Promise<ManualPaymentInstructionsActionState>;
  saveManualPaymentInstructionsAction: (
    previousState: ManualPaymentInstructionsActionState,
    formData: FormData,
  ) => Promise<ManualPaymentInstructionsActionState>;
};

export function PaymentSetupActionSurface({
  canManage,
  hidePrimaryAuthorization = false,
  organizerId,
  providerConnectionTests = [],
  runProviderConnectionTestAction,
  startAuthorizationAction,
  status,
}: PaymentSetupActionSurfaceProps) {
  const facts = paymentSetupFacts(status);
  const latestConnectionTest = providerConnectionTests[0] ?? null;
  const secondaryActions = hidePrimaryAuthorization
    ? status.providerAuthorizationActions.filter(
        (action) => providerAuthorizationActionKind(action.id) !== "start",
      )
    : status.providerAuthorizationActions;

  if (!canManage) {
    return (
      <div
        className="payment-setup-readonly-panel"
        aria-label="Payment Setup access"
      >
        <span>Access</span>
        <strong>Read-only for Operators</strong>
        <p>{status.paymentSetupAccessMessage}</p>
        <PaymentSetupFactGrid facts={facts} />
      </div>
    );
  }

  if (!secondaryActions.length) {
    return null;
  }

  return (
    <section
      className="payment-setup-action-surface"
      aria-label="Razorpay actions"
    >
      <div className="payment-setup-owner-actions">
        <div>
          <span>Owner actions</span>
          <strong>Razorpay actions</strong>
          <p>
            Use these only when access changes or verification needs a refresh.
          </p>
        </div>
        <div className="payment-setup-action-list" role="list">
          {secondaryActions.map((authorizationAction) => (
            <PaymentSetupActionButton
              key={authorizationAction.id}
              action={authorizationAction}
              organizerId={organizerId}
              providerConnectionTestAction={runProviderConnectionTestAction}
              providerAuthorizationAction={startAuthorizationAction}
              providerMode={status.providerMode}
            />
          ))}
        </div>
        <ProviderConnectionTestSummary result={latestConnectionTest} />
      </div>
    </section>
  );
}

export function PaymentSetupPrimaryAuthorizationAction({
  canManage,
  organizerId,
  startAuthorizationAction,
  status,
}: PaymentSetupActionSurfaceProps) {
  const authorizationAction = status.providerAuthorizationActions.find(
    (action) => providerAuthorizationActionKind(action.id) === "start",
  );

  if (!canManage) {
    return (
      <div className="payment-setup-hero-action is-readonly">
        <span>Owner action required</span>
        <strong>Only Owners can authorize Razorpay.</strong>
      </div>
    );
  }

  if (!authorizationAction) {
    return (
      <div className="payment-setup-hero-action is-readonly">
        <span>Authorization unavailable</span>
        <strong>Razorpay authorization cannot be started right now.</strong>
      </div>
    );
  }

  return (
    <div className="payment-setup-hero-action">
      <PaymentSetupAuthorizationForm
        action={authorizationAction}
        label={primaryAuthorizationLabel(status)}
        organizerId={organizerId}
        providerAuthorizationAction={startAuthorizationAction}
        providerMode={status.providerMode}
      />
      <span>{authorizationAction.statusLabel}</span>
    </div>
  );
}

export function ManualPaymentInstructionsPanel({
  canManage,
  instructions,
  organizerId,
  removeManualPaymentInstructionsAction,
  saveManualPaymentInstructionsAction,
}: ManualPaymentInstructionsPanelProps) {
  const statusTone = instructions.ready ? "is-clear" : "is-blocked";

  return (
    <section
      className="manual-payment-instructions-panel"
      aria-labelledby="manual-payment-instructions-title"
    >
      <div className="payment-method-card-heading">
        <div className="payment-method-card-icon is-manual">
          <QrCode aria-hidden="true" />
        </div>
        <div>
          <p className="eyebrow">Manual Payments</p>
          <h3 id="manual-payment-instructions-title">
            Manual Payment Instructions
          </h3>
          <p>{instructions.message}</p>
        </div>
        <span className={`status-chip ${statusTone}`}>
          {instructions.statusLabel}
        </span>
      </div>

      <div className="manual-payment-instructions-body">
        <PaymentQrPreview instructions={instructions} />
        {canManage ? (
          <ManualPaymentInstructionsEditor
            instructions={instructions}
            organizerId={organizerId}
            removeManualPaymentInstructionsAction={
              removeManualPaymentInstructionsAction
            }
            saveManualPaymentInstructionsAction={
              saveManualPaymentInstructionsAction
            }
          />
        ) : (
          <ManualPaymentInstructionsReadOnly instructions={instructions} />
        )}
      </div>
    </section>
  );
}

function PaymentQrPreview({
  instructions,
}: {
  instructions: ManualPaymentInstructions;
}) {
  if (!instructions.paymentQrUploaded || !instructions.paymentQrUrl) {
    return (
      <div className="payment-qr-preview is-empty">
        <QrCode aria-hidden="true" />
        <strong>Payment QR missing</strong>
        <span>Manual Payments stay blocked until an Owner uploads one.</span>
      </div>
    );
  }

  return (
    <figure className="payment-qr-preview">
      <img alt="Payment QR" src={instructions.paymentQrUrl} />
      <figcaption>
        <strong>Payment QR uploaded</strong>
        <span>
          {instructions.originalFilename || "Ready for Manual Payments"}
        </span>
      </figcaption>
    </figure>
  );
}

function ManualPaymentInstructionsEditor({
  instructions,
  organizerId,
  removeManualPaymentInstructionsAction,
  saveManualPaymentInstructionsAction,
}: Omit<ManualPaymentInstructionsPanelProps, "canManage">) {
  const [saveState, saveAction] = useFormState(
    saveManualPaymentInstructionsAction,
    initialManualPaymentInstructionsState,
  );
  const [removeState, removeAction] = useFormState(
    removeManualPaymentInstructionsAction,
    initialManualPaymentInstructionsState,
  );

  return (
    <div className="manual-payment-instructions-editor">
      <form action={saveAction} className="payment-setup-form">
        <input name="organizerId" type="hidden" value={organizerId} />
        <label>
          <span>Payment QR</span>
          <input
            accept="image/png,image/jpeg,image/webp"
            name="payment_qr"
            type="file"
          />
        </label>
        <div className="manual-payment-instructions-grid">
          <label>
            <span>UPI ID</span>
            <input
              defaultValue={instructions.upiId}
              maxLength={80}
              name="upi_id"
              placeholder="name@bank"
              type="text"
            />
          </label>
          <label>
            <span>Account name</span>
            <input
              defaultValue={instructions.accountName}
              maxLength={160}
              name="account_name"
              placeholder="Organizer payout name"
              type="text"
            />
          </label>
        </div>
        <label>
          <span>Bank transfer details</span>
          <textarea
            defaultValue={instructions.bankTransferDetails}
            maxLength={600}
            name="bank_transfer_details"
            placeholder="Concise bank transfer details"
            rows={4}
          />
        </label>
        <ManualPaymentInstructionsSubmitButton />
        <PaymentSetupFormState state={saveState} />
      </form>

      {instructions.paymentQrUploaded ||
      instructions.upiId ||
      instructions.accountName ||
      instructions.bankTransferDetails ? (
        <form action={removeAction} className="manual-payment-remove-form">
          <input name="organizerId" type="hidden" value={organizerId} />
          <ManualPaymentInstructionsRemoveButton />
          <PaymentSetupFormState state={removeState} />
        </form>
      ) : null}
    </div>
  );
}

function ManualPaymentInstructionsSubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      className="payment-setup-action-button is-primary"
      disabled={pending}
      type="submit"
    >
      <Upload aria-hidden="true" />
      {pending ? "Saving..." : "Save Manual Payment Instructions"}
    </button>
  );
}

function ManualPaymentInstructionsRemoveButton() {
  const { pending } = useFormStatus();

  return (
    <button
      className="payment-setup-action-button is-danger"
      disabled={pending}
      type="submit"
    >
      <Trash2 aria-hidden="true" />
      {pending ? "Removing..." : "Remove Manual Payment Instructions"}
    </button>
  );
}

function PaymentSetupFormState({
  state,
}: {
  state: ManualPaymentInstructionsActionState;
}) {
  if (state.error) {
    return (
      <div className="auth-error payment-setup-action-error" role="alert">
        {state.error}
      </div>
    );
  }

  if (state.message) {
    return <p className="payment-setup-success-message">{state.message}</p>;
  }

  return null;
}

function ManualPaymentInstructionsReadOnly({
  instructions,
}: {
  instructions: ManualPaymentInstructions;
}) {
  const details = [
    {
      label: "UPI ID",
      value: instructions.upiId || "Not provided",
      icon: QrCode,
    },
    {
      label: "Account name",
      value: instructions.accountName || "Not provided",
      icon: Banknote,
    },
    {
      label: "Bank transfer details",
      value: instructions.bankTransferDetails || "Not provided",
      icon: Banknote,
    },
  ];

  return (
    <div
      className="manual-payment-readonly"
      aria-label="Manual Payment Instructions details"
    >
      <strong>Read-only for Operators</strong>
      <p>Only Owners can edit Organizer-level Manual Payment Instructions.</p>
      <dl>
        {details.map((detail) => {
          const Icon = detail.icon;
          return (
            <div key={detail.label}>
              <dt>
                <Icon aria-hidden="true" />
                {detail.label}
              </dt>
              <dd>{detail.value}</dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

function PaymentSetupActionButton({
  action,
  organizerId,
  providerAuthorizationAction,
  providerConnectionTestAction,
  providerMode,
}: {
  action: PaymentSetupActionDescriptor;
  organizerId: number;
  providerConnectionTestAction: (
    previousState: ProviderConnectionTestActionState,
    formData: FormData,
  ) => Promise<ProviderConnectionTestActionState>;
  providerAuthorizationAction: (
    previousState: ProviderAuthorizationActionState,
    formData: FormData,
  ) => Promise<ProviderAuthorizationActionState>;
  providerMode: string;
}) {
  const Icon = actionIcons[action.id] ?? CircleOff;
  const actionKind = paymentSetupActionKind(action.id);

  return (
    <div className="payment-setup-action-row" role="listitem">
      {actionKind === "start_authorization" ? (
        <PaymentSetupAuthorizationForm
          action={action}
          organizerId={organizerId}
          providerAuthorizationAction={providerAuthorizationAction}
          providerMode={providerMode}
        />
      ) : actionKind === "test_connection" ? (
        <ProviderConnectionTestForm
          action={action}
          icon={Icon}
          organizerId={organizerId}
          providerConnectionTestAction={providerConnectionTestAction}
        />
      ) : (
        <button
          className={`payment-setup-action-button is-${action.tone}`}
          disabled
          type="button"
        >
          <Icon aria-hidden="true" />
          {action.label}
        </button>
      )}
      <span className="status-chip is-neutral">{action.statusLabel}</span>
      <p>{action.description}</p>
    </div>
  );
}

function ProviderConnectionTestForm({
  action,
  icon: Icon,
  organizerId,
  providerConnectionTestAction,
}: {
  action: PaymentSetupActionDescriptor;
  icon: LucideIcon;
  organizerId: number;
  providerConnectionTestAction: (
    previousState: ProviderConnectionTestActionState,
    formData: FormData,
  ) => Promise<ProviderConnectionTestActionState>;
}) {
  const [state, formAction] = useFormState(
    providerConnectionTestAction,
    initialProviderConnectionTestState,
  );

  return (
    <form action={formAction} className="payment-setup-action-form">
      <input name="organizerId" type="hidden" value={organizerId} />
      <PaymentSetupActionSubmitButton
        action={action}
        disabled={!action.enabled}
        icon={Icon}
        loadingLabel="Testing..."
      />
      <ProviderConnectionTestFormState state={state} />
    </form>
  );
}

function ProviderConnectionTestFormState({
  state,
}: {
  state: ProviderConnectionTestActionState;
}) {
  if (state.error) {
    return (
      <div className="auth-error payment-setup-action-error" role="alert">
        {state.error}
      </div>
    );
  }

  if (state.message) {
    return <p className="payment-setup-success-message">{state.message}</p>;
  }

  return null;
}

function PaymentSetupAuthorizationForm({
  action,
  label,
  organizerId,
  providerAuthorizationAction,
  providerMode,
}: {
  action: PaymentSetupActionDescriptor;
  label?: string;
  organizerId: number;
  providerAuthorizationAction: (
    previousState: ProviderAuthorizationActionState,
    formData: FormData,
  ) => Promise<ProviderAuthorizationActionState>;
  providerMode: string;
}) {
  const Icon = actionIcons[action.id] ?? Plug;
  const [state, formAction] = useFormState(
    providerAuthorizationAction,
    initialProviderAuthorizationState,
  );

  return (
    <form action={formAction} className="payment-setup-action-form">
      <input name="organizerId" type="hidden" value={organizerId} />
      <input name="providerMode" type="hidden" value={providerMode} />
      <PaymentSetupActionSubmitButton
        action={action}
        disabled={!action.enabled}
        icon={Icon}
        label={label}
      />
      {state.error ? (
        <div className="auth-error payment-setup-action-error" role="alert">
          {state.error}
        </div>
      ) : null}
    </form>
  );
}

function PaymentSetupActionSubmitButton({
  action,
  disabled,
  icon: Icon,
  label,
  loadingLabel = "Starting...",
}: {
  action: PaymentSetupActionDescriptor;
  disabled: boolean;
  icon: LucideIcon;
  label?: string;
  loadingLabel?: string;
}) {
  const { pending } = useFormStatus();

  return (
    <button
      className={`payment-setup-action-button is-${action.tone}`}
      disabled={disabled || pending}
      type="submit"
    >
      <Icon aria-hidden="true" />
      {pending ? loadingLabel : (label ?? action.label)}
    </button>
  );
}

function ProviderConnectionTestSummary({
  result,
}: {
  result: ProviderConnectionTestResult | null;
}) {
  if (!result) {
    return (
      <div className="provider-connection-test-summary is-empty">
        <span>Latest Provider Connection Test</span>
        <strong>No test run yet</strong>
        <p>Run a test after Provider Authorization is available.</p>
      </div>
    );
  }

  const succeeded = result.status === "succeeded";
  const completedAt = formatConnectionTestTime(
    result.completedAt || result.startedAt,
  );

  return (
    <div
      className={`provider-connection-test-summary ${
        succeeded ? "is-clear" : "is-blocked"
      }`}
    >
      <span>Latest Provider Connection Test</span>
      <div>
        <strong>{result.statusLabel}</strong>
        <em>{completedAt}</em>
      </div>
      <p>
        {result.passedCheckCount} passed
        {result.failedCheckCount ? `, ${result.failedCheckCount} failed` : ""}
        {result.skippedCheckCount
          ? `, ${result.skippedCheckCount} skipped`
          : ""}
        {result.failureReason ? ` (${result.failureReason})` : ""}
      </p>
    </div>
  );
}

function formatConnectionTestTime(value: string): string {
  if (!value) {
    return "Time not recorded";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    timeZone: "Asia/Kolkata",
    year: "numeric",
  }).format(new Date(value));
}

function primaryAuthorizationLabel(status: PaymentSetupStatus): string {
  return `Connect ${status.providerLabel || "Razorpay"}`;
}

function PaymentSetupFactGrid({ facts }: { facts: PaymentSetupFact[] }) {
  return (
    <dl className="payment-setup-readonly-grid">
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd>
            <span
              className={`status-dot ${fact.clear ? "is-clear" : "is-blocked"}`}
            />
            {fact.value}
          </dd>
          <p>{fact.detail}</p>
        </div>
      ))}
    </dl>
  );
}

function paymentSetupFacts(status: PaymentSetupStatus): PaymentSetupFact[] {
  return [
    {
      label: "Provider Authorization",
      value: status.providerAuthorizationStateLabel,
      detail: status.providerAuthorizationMethodLabel,
      clear: status.providerAuthorizationState === "authorized",
    },
    {
      label: "Provider Mode",
      value: status.providerModeLabel,
      detail: "Live Provider Mode is required before public booking can open.",
      clear: status.providerMode === "live",
    },
    {
      label: "Provider Verification",
      value: status.providerVerificationStatusLabel,
      detail: "Provider Verification is confirmed by Razorpay.",
      clear: status.providerVerificationStatus === "verified",
    },
    {
      label: "Settlement Readiness",
      value: status.settlementReadinessStatusLabel,
      detail: "Settled provider payments can be received by the Organizer.",
      clear: status.settlementReadinessReady,
    },
    {
      label: "Provider Connection State",
      value: status.providerConnectionStateLabel,
      detail: "TripOS can reach the connected provider account.",
      clear: status.providerConnectionState === "healthy",
    },
    {
      label: "Provider Payment Capability",
      value: status.providerPaymentCapabilityEnabled ? "Enabled" : "Disabled",
      detail:
        "TripOS can create payment attempts and confirm captured payments.",
      clear: status.providerPaymentCapabilityEnabled,
    },
    {
      label: "Online Payment Readiness",
      value: status.onlinePaymentReadinessStatusLabel,
      detail: status.onlinePaymentReadinessMessage,
      clear: status.onlinePaymentReadinessReady,
    },
  ];
}
