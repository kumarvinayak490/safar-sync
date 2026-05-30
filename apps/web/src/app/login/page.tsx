import type { Metadata } from "next";

import { AuthEntryForm } from "@/app/AuthEntryForm";

import { loginAction } from "./actions";

export const metadata: Metadata = {
  title: "Log in | TripOS",
  description: "Log in to TripOS trip operations",
};

export default function LoginPage() {
  return (
    <main className="auth-shell">
      <AuthStoryPanel />
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-brand">
          <span>TripOS</span>
          <strong>Organizer access</strong>
        </div>
        <div className="auth-heading">
          <p className="eyebrow">Welcome back</p>
          <h1 id="login-title">Log in to Organizer Home</h1>
          <p>Open your operations workspace.</p>
        </div>
        <AuthEntryForm action={loginAction} mode="login" />
      </section>
    </main>
  );
}

function AuthStoryPanel() {
  return (
    <section className="auth-story" aria-label="TripOS product context">
      <div>
        <p className="eyebrow">Operator ready</p>
        <h2>Know what needs action.</h2>
        <p>Payments, readiness, launch, exports.</p>
      </div>
      <dl className="auth-ledger">
        <div>
          <dt>Unpaid Bookings</dt>
          <dd>Follow-ups visible</dd>
        </div>
        <div>
          <dt>Traveler Readiness</dt>
          <dd>Requirements clear</dd>
        </div>
        <div>
          <dt>Exports</dt>
          <dd>Auditable handoffs</dd>
        </div>
      </dl>
    </section>
  );
}
