import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { currentSession } from "@/lib/auth";
import { organizerOnboardingRedirect } from "@/lib/auth-routing";

import { createOrganizerAction } from "./actions";
import { OrganizerOnboardingForm } from "./OrganizerOnboardingForm";

export const metadata: Metadata = {
  title: "Create Organizer | TripOS",
  description:
    "Create the Organizer workspace that owns TripOS trips and operations",
};

export default async function OrganizerOnboardingPage() {
  const session = await currentSession();
  const redirectTo = organizerOnboardingRedirect(session);

  if (redirectTo) {
    redirect(redirectTo);
  }

  const user = session?.user;
  const ownerName =
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
    user?.email ||
    "Owner";

  return (
    <main className="onboarding-shell">
      <section
        className="onboarding-workbench"
        aria-labelledby="organizer-title"
      >
        <div className="onboarding-rail" aria-label="Onboarding steps">
          <div className="auth-brand">
            <span>TripOS</span>
            <strong>Organizer onboarding</strong>
          </div>
          <ol className="step-list">
            <li aria-current="step">
              <span>01</span>
              <strong>Organizer</strong>
              <em>Owner membership and Organizer Identity</em>
            </li>
          </ol>
        </div>

        <section className="onboarding-main">
          <div className="onboarding-heading">
            <p className="eyebrow">Organizer onboarding</p>
            <h1 id="organizer-title">Create your Organizer</h1>
            <p>Name the group that owns Trip operations.</p>
          </div>

          <div className="onboarding-panel">
            <div className="setup-grid">
              <div>
                <span>Ownership</span>
                <strong>Owner membership</strong>
                <em>You become the first Owner.</em>
              </div>
              <div>
                <span>Public identity</span>
                <strong>Defaults from name</strong>
                <em>Edit later.</em>
              </div>
            </div>

            <OrganizerOnboardingForm
              action={createOrganizerAction}
              ownerName={ownerName}
            />
          </div>
        </section>
      </section>
    </main>
  );
}
