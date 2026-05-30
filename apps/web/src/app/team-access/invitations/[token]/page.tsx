import Link from "next/link";

import { acceptInvitationAction } from "@/app/team-access/actions";
import { InvitationAcceptForm } from "@/app/team-access/InvitationAcceptForm";
import { currentSession } from "@/lib/auth";
import { getOrganizerInvitation } from "@/lib/team-access";

export const metadata = {
  title: "Accept Organizer Invitation | TripOS",
  description: "Accept a TripOS Organizer Invitation"
};

export default async function OrganizerInvitationPage({
  params
}: {
  params: { token: string };
}) {
  const invitation = await getOrganizerInvitation(params.token);
  const session = await currentSession();
  const isAuthenticated = Boolean(session?.authenticated);

  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="Organizer Invitation context">
        <div>
          <p className="eyebrow">Organizer Invitation</p>
          <h2>Join the Organizer before you pick up trip work.</h2>
          <p>
            TripOS keeps your login User separate from the Organizer Membership
            you are accepting here.
          </p>
        </div>
        <dl className="auth-ledger">
          <div>
            <dt>Role</dt>
            <dd>{invitation.ok ? invitation.invitation.roleLabel : "Pending access"}</dd>
          </div>
          <div>
            <dt>Organizer</dt>
            <dd>{invitation.ok ? invitation.invitation.organizer?.name : "Not available"}</dd>
          </div>
          <div>
            <dt>User</dt>
            <dd>{isAuthenticated ? "Signed in" : "Sign in or create your User"}</dd>
          </div>
        </dl>
      </section>

      <section className="auth-panel" aria-labelledby="invite-title">
        <div className="auth-brand">
          <span>TripOS</span>
          <strong>Team Access</strong>
        </div>
        {invitation.ok ? (
          <>
            <div className="auth-heading">
              <p className="eyebrow">Invitation</p>
              <h1 id="invite-title">
                Join {invitation.invitation.organizer?.name}
              </h1>
              <p>
                This Organizer Invitation adds your signed-in User as{" "}
                {article(invitation.invitation.roleLabel)}{" "}
                {invitation.invitation.roleLabel}.
              </p>
            </div>
            {isAuthenticated ? (
              <InvitationAcceptForm
                action={acceptInvitationAction}
                token={params.token}
              />
            ) : (
              <div className="team-access-accept-links">
                <Link className="primary-link-button" href="/login">
                  Log in
                </Link>
                <Link className="secondary-link-button" href="/signup">
                  Create User
                </Link>
                <p>
                  After authentication, return to this invitation link to accept
                  the Organizer Membership.
                </p>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="auth-heading">
              <p className="eyebrow">Invitation</p>
              <h1 id="invite-title">Invitation unavailable</h1>
              <p>{invitation.message}</p>
            </div>
            <Link className="secondary-link-button" href="/login">
              Back to login
            </Link>
          </>
        )}
      </section>
    </main>
  );
}

function article(roleLabel: string): string {
  return /^[aeiou]/i.test(roleLabel) ? "an" : "a";
}
