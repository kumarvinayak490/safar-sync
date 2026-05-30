import type { Metadata } from "next";

import { AuthEntryForm } from "@/app/AuthEntryForm";

import { signupAction } from "./actions";

export const metadata: Metadata = {
  title: "Create User | TripOS",
  description: "Create a local TripOS User for paid group trip operations"
};

export default function SignupPage() {
  return (
    <main className="auth-shell">
      <AuthStoryPanel />
      <section className="auth-panel" aria-labelledby="signup-title">
        <div className="auth-brand">
          <span>TripOS</span>
          <strong>Organizer access</strong>
        </div>
        <div className="auth-heading">
          <p className="eyebrow">Local MVP</p>
          <h1 id="signup-title">Create your User</h1>
          <p>Create your Organizer next.</p>
        </div>
        <AuthEntryForm action={signupAction} mode="signup" />
      </section>
    </main>
  );
}

function AuthStoryPanel() {
  return (
    <section className="auth-story" aria-label="TripOS product context">
      <div>
        <p className="eyebrow">For repeat paid trips</p>
        <h2>One operating record per Trip.</h2>
        <p>Payments, seats, readiness, reminders, exports.</p>
      </div>
      <dl className="auth-ledger">
        <div>
          <dt>Booking State</dt>
          <dd>Reserved before confirmed</dd>
        </div>
        <div>
          <dt>Payment Setup</dt>
          <dd>Provider readiness gates bookings</dd>
        </div>
        <div>
          <dt>Operator View</dt>
          <dd>Clear queues for field work</dd>
        </div>
      </dl>
    </section>
  );
}
