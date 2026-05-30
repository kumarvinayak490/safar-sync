import { Plug } from "lucide-react";

import { OperationsWorkspaceShell } from "@/app/OperationsWorkspaceShell";
import {
  ManualPaymentInstructionsPanel,
  PaymentSetupActionSurface,
  PaymentSetupPrimaryAuthorizationAction,
} from "@/app/payment-setup/PaymentSetupForm";
import {
  removeManualPaymentInstructionsAction,
  runProviderConnectionTestAction,
  saveManualPaymentInstructionsAction,
  startProviderAuthorizationAction,
} from "@/app/payment-setup/actions";
import { loadWorkspace } from "@/app/workspace";
import { getOperationsDashboard } from "@/lib/operations-dashboard";
import {
  getProviderConnectionTests,
  normalizePaymentSetupStatus,
} from "@/lib/payment-setup";

export const metadata = {
  title: "Payment Setup | TripOS",
  description: "TripOS Organizer-level Payment Setup",
};

export default async function PaymentSetupPage() {
  const workspace = await loadWorkspace();
  const dashboard = await getOperationsDashboard();
  const paymentSetup = dashboard.ok
    ? dashboard.paymentSetup
    : normalizePaymentSetupStatus();
  const canManage = dashboard.ok
    ? dashboard.permissions.canManagePaymentSetup
    : workspace.organizer.membership_role === "owner";
  const providerConnectionTests = canManage
    ? await getProviderConnectionTests(workspace.organizer.id)
    : [];
  const setupMethodReady =
    paymentSetup.onlinePaymentReadinessReady ||
    paymentSetup.manualPaymentInstructions.ready;
  const statusTone = setupMethodReady ? "is-clear" : "is-blocked";
  const onlineReady = paymentSetup.onlinePaymentReadinessReady;
  const paymentQrReady = paymentSetup.manualPaymentInstructions.ready;
  const heroTitle =
    onlineReady && paymentQrReady
      ? "Payment methods ready"
      : paymentQrReady
        ? "Payment QR ready"
        : onlineReady
          ? "Razorpay ready"
          : "Set up a payment method";
  const heroBody =
    onlineReady && paymentQrReady
      ? "Use Launch to choose what travelers can use."
      : paymentQrReady
        ? "Open booking from Launch. Connect Razorpay later."
        : onlineReady
          ? "Open booking from Launch."
          : "Upload a Payment QR or connect Razorpay.";

  return (
    <OperationsWorkspaceShell
      activePath="/payment-setup"
      currentPath="/payment-setup"
      workspace={workspace}
    >
      <section
        className="payment-setup-page"
        aria-labelledby="payment-setup-title"
      >
        <section
          className={`payment-setup-readiness-hero ${statusTone}`}
          aria-label="Payment readiness"
        >
          <div className="payment-setup-hero-copy">
            <div className="payment-setup-hero-kicker">
              <p className="eyebrow">Payment Setup</p>
              <span className={`status-chip ${statusTone}`}>
                {setupMethodReady ? "Ready" : "Needs setup"}
              </span>
            </div>
            <h2 id="payment-setup-title">{heroTitle}</h2>
            <p>{heroBody}</p>
            {!setupMethodReady ? (
              <em>{paymentSetup.manualPaymentInstructions.blockerLabel}</em>
            ) : null}
          </div>
          <PaymentSetupPrimaryAuthorizationAction
            canManage={canManage}
            organizerId={workspace.organizer.id}
            runProviderConnectionTestAction={runProviderConnectionTestAction}
            startAuthorizationAction={startProviderAuthorizationAction}
            status={paymentSetup}
          />
        </section>

        <section
          className="payment-method-surfaces"
          aria-label="Payment methods"
        >
          <section
            className="payment-method-card"
            aria-labelledby="razorpay-method-title"
          >
            <div className="payment-method-card-heading">
              <div className="payment-method-card-icon">
                <Plug aria-hidden="true" />
              </div>
              <div>
                <p className="eyebrow">Razorpay online payments</p>
                <h3 id="razorpay-method-title">Online payments</h3>
                <p>{paymentSetup.providerPaymentMethod.message}</p>
              </div>
              <span
                className={`status-chip ${
                  paymentSetup.providerPaymentMethod.ready
                    ? "is-clear"
                    : "is-blocked"
                }`}
              >
                {paymentSetup.providerPaymentMethod.statusLabel}
              </span>
            </div>
            <dl className="payment-method-readiness-list">
              <div>
                <dt>Provider</dt>
                <dd>{paymentSetup.providerLabel}</dd>
              </div>
              <div>
                <dt>Blocker</dt>
                <dd>{paymentSetup.providerPaymentMethod.blockerLabel}</dd>
              </div>
              <div>
                <dt>Traveler action</dt>
                <dd>{paymentSetup.providerPaymentMethod.actionLabel}</dd>
              </div>
            </dl>
          </section>

          <ManualPaymentInstructionsPanel
            canManage={canManage}
            instructions={paymentSetup.manualPaymentInstructions}
            organizerId={workspace.organizer.id}
            removeManualPaymentInstructionsAction={
              removeManualPaymentInstructionsAction
            }
            saveManualPaymentInstructionsAction={
              saveManualPaymentInstructionsAction
            }
          />
        </section>

        <PaymentSetupActionSurface
          canManage={canManage}
          hidePrimaryAuthorization
          organizerId={workspace.organizer.id}
          providerConnectionTests={providerConnectionTests}
          runProviderConnectionTestAction={runProviderConnectionTestAction}
          startAuthorizationAction={startProviderAuthorizationAction}
          status={paymentSetup}
        />
      </section>
    </OperationsWorkspaceShell>
  );
}
