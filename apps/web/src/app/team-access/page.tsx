import { Ban, RotateCcw, ShieldCheck, UserRoundCheck } from "lucide-react";

import {
  createInvitationAction,
  resendInvitationAction,
  revokeInvitationAction
} from "@/app/team-access/actions";
import { TeamAccessInviteForm } from "@/app/team-access/TeamAccessInviteForm";
import {
  OperationalEmptyState,
  OperationsWorkspaceShell
} from "@/app/OperationsWorkspaceShell";
import { loadWorkspace } from "@/app/workspace";
import { getOperationsDashboard } from "@/lib/operations-dashboard";
import { getTeamAccess, type OrganizerInvitationSummary } from "@/lib/team-access";

export const metadata = {
  title: "Team Access | TripOS",
  description: "TripOS Owner and Operator access"
};

export default async function TeamAccessPage() {
  const workspace = await loadWorkspace();
  const dashboard = await getOperationsDashboard();
  const organizerId = dashboard.ok
    ? dashboard.activeOrganizer.id
    : workspace.organizer.id;
  const isOwner = dashboard.ok
    ? dashboard.permissions.canManageTeamAccess
    : workspace.organizer.membership_role === "owner";
  const teamAccess = await getTeamAccess(organizerId);

  if (!teamAccess.ok) {
    return (
      <OperationsWorkspaceShell
        activePath="/team-access"
        currentPath="/team-access"
        workspace={workspace}
      >
        <OperationalEmptyState
          eyebrow="Team Access"
          title="Team Access is not available"
          body={teamAccess.message}
        />
      </OperationsWorkspaceShell>
    );
  }

  const memberships = teamAccess.teamAccess.memberships;
  const invitations = teamAccess.teamAccess.pendingInvitations;

  return (
    <OperationsWorkspaceShell
      activePath="/team-access"
      currentPath="/team-access"
      workspace={workspace}
    >
      <section className="team-access-page" aria-labelledby="team-access-title">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">Team Access</p>
            <h2 id="team-access-title">Owner and Operator access</h2>
            <p className="workspace-heading-copy">Memberships and invitations.</p>
          </div>
          <span className={`status-chip ${isOwner ? "is-clear" : "is-readonly"}`}>
            {isOwner ? "Owner managed" : "Read-only"}
          </span>
        </div>

        <section className="team-access-summary" aria-label="Access summary">
          <div>
            <UserRoundCheck aria-hidden="true" />
            <span>Active memberships</span>
            <strong>{memberships.length}</strong>
            <em>{teamAccess.teamAccess.ownerCount} Owner minimum</em>
          </div>
          <div>
            <ShieldCheck aria-hidden="true" />
            <span>Pending invitations</span>
            <strong>{invitations.length}</strong>
            <em>Resend or revoke.</em>
          </div>
          <div>
            <ShieldCheck aria-hidden="true" />
            <span>Your role</span>
            <strong>{workspace.roleLabel}</strong>
            <em>
              {isOwner
                ? "Manage access."
                : "View only."}
            </em>
          </div>
        </section>

        <div className="team-access-layout">
          <section className="team-access-panel" aria-labelledby="memberships-title">
            <div>
              <p className="eyebrow">Organizer Memberships</p>
              <h3 id="memberships-title">Active team</h3>
            </div>
            <div className="team-access-list">
              {memberships.map((membership) => (
                <article key={membership.id} className="team-access-row">
                  <div className="team-access-avatar" aria-hidden="true">
                    {initials(membership.user.name)}
                  </div>
                  <div>
                    <strong>{membership.user.name}</strong>
                    <span>{membership.user.email}</span>
                  </div>
                  <span
                    className={`status-chip ${
                      membership.role === "owner" ? "is-clear" : "is-readonly"
                    }`}
                  >
                    {membership.roleLabel}
                  </span>
                </article>
              ))}
            </div>
          </section>

          <section className="team-access-panel" aria-labelledby="invite-title">
            <div>
              <p className="eyebrow">Organizer Invitations</p>
              <h3 id="invite-title">{isOwner ? "Invite by email" : "Invitation status"}</h3>
            </div>
            {isOwner ? (
              <TeamAccessInviteForm
                action={createInvitationAction}
                organizerId={organizerId}
              />
            ) : (
              <div className="team-access-note" aria-label="Team Access controls">
                <span>Access</span>
                <strong>Read-only for Operators</strong>
                <p>
                  Owner action required.
                </p>
              </div>
            )}
          </section>
        </div>

        <section className="team-access-panel" aria-labelledby="pending-title">
          <div>
            <p className="eyebrow">Pending</p>
            <h3 id="pending-title">Organizer Invitations</h3>
          </div>
          {invitations.length ? (
            <div className="team-access-list">
              {invitations.map((invitation) => (
                <PendingInvitationRow
                  invitation={invitation}
                  isOwner={isOwner}
                  key={invitation.id}
                  organizerId={organizerId}
                />
              ))}
            </div>
          ) : (
            <div className="team-access-empty">
              <strong>No pending invitations</strong>
              <span>
                No invites waiting.
              </span>
            </div>
          )}
        </section>
      </section>
    </OperationsWorkspaceShell>
  );
}

function PendingInvitationRow({
  invitation,
  isOwner,
  organizerId
}: {
  invitation: OrganizerInvitationSummary;
  isOwner: boolean;
  organizerId: number;
}) {
  return (
    <article className="team-access-row">
      <div className="team-access-avatar is-pending" aria-hidden="true">
        {initials(invitation.email)}
      </div>
      <div>
        <strong>{invitation.email}</strong>
        <span>
          {invitation.roleLabel} invitation
          {invitation.inviteUrlPath ? `, ${invitation.inviteUrlPath}` : ""}
        </span>
      </div>
      <span
        className={`status-chip ${
          invitation.role === "owner" ? "is-blocked" : "is-readonly"
        }`}
      >
        {invitation.roleLabel}
      </span>
      {isOwner ? (
        <div className="team-access-row-actions">
          <form action={resendInvitationAction}>
            <input name="organizerId" type="hidden" value={organizerId} />
            <input name="invitationId" type="hidden" value={invitation.id} />
            <button className="secondary-button icon-link" type="submit">
              <RotateCcw aria-hidden="true" />
              Resend
            </button>
          </form>
          <form action={revokeInvitationAction}>
            <input name="organizerId" type="hidden" value={organizerId} />
            <input name="invitationId" type="hidden" value={invitation.id} />
            <button className="identity-danger-button icon-link" type="submit">
              <Ban aria-hidden="true" />
              Revoke
            </button>
          </form>
        </div>
      ) : null}
    </article>
  );
}

function initials(value: string): string {
  const initialsValue = value
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return initialsValue || "TA";
}
