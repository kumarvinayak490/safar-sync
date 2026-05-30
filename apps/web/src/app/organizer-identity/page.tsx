import { Image as ImageIcon, MessageCircle, ShieldCheck } from "lucide-react";

import { OrganizerIdentityForm } from "@/app/organizer-identity/OrganizerIdentityForm";
import { saveOrganizerIdentityAction } from "@/app/organizer-identity/actions";
import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import { loadWorkspace } from "@/app/workspace";
import { getOperationsDashboard } from "@/lib/operations-dashboard";

export const metadata = {
  title: "Organizer Identity | TripOS",
  description: "TripOS Organizer Identity",
};

export default async function OrganizerIdentityPage() {
  const workspace = await loadWorkspace();
  const dashboard = await getOperationsDashboard();

  if (!dashboard.ok) {
    return (
      <OperationsWorkspaceShell
        activePath="/organizer-identity"
        currentPath="/organizer-identity"
        workspace={workspace}
      >
        <OperationalEmptyState
          eyebrow="Organizer Identity"
          title="Organizer Identity is not available"
          body="Your User does not have access to this Organizer setting."
        />
      </OperationsWorkspaceShell>
    );
  }

  const identity = dashboard.activeOrganizer.identity;
  const canManage = dashboard.permissions.canManageOrganizerIdentity;

  return (
    <OperationsWorkspaceShell
      activePath="/organizer-identity"
      currentPath="/organizer-identity"
      workspace={workspace}
    >
      <section className="identity-settings-page" aria-labelledby="identity-title">
        <div className="workspace-heading">
          <div>
            <p className="eyebrow">Organizer Identity</p>
            <h2 id="identity-title">Traveler-facing identity</h2>
          </div>
          <span
            className={`status-chip ${
              identity.logoUploaded ? "is-clear" : "is-readonly"
            }`}
          >
            {identity.logoUploaded ? "Logo added" : "Text fallback active"}
          </span>
        </div>

        <div className="identity-settings-layout">
          <section className="identity-preview-panel" aria-label="Traveler-facing preview">
            <IdentityMark identity={identity} />
            <div>
              <span>Public display</span>
              <strong>{identity.name}</strong>
              <p>
                {identity.logoUploaded
                  ? "Logo active."
                  : "Text fallback active."}
              </p>
              <p>
                {identity.hasWhatsappNumber
                  ? `WhatsApp ${identity.whatsappNumber}`
                  : "WhatsApp number not added."}
              </p>
            </div>
          </section>

          <section className="identity-editor-panel" aria-label="Organizer Identity editor">
            <div>
              <p className="eyebrow">Settings</p>
              <h3>{canManage ? "Manage identity" : "Identity status"}</h3>
            </div>
            <OrganizerIdentityForm
              action={saveOrganizerIdentityAction}
              canManage={canManage}
              identity={identity}
              organizerId={dashboard.activeOrganizer.id}
            />
          </section>
        </div>

        <section className="identity-metadata-strip" aria-label="Fallback metadata">
          <div>
            <ImageIcon aria-hidden="true" />
            <span>Fallback</span>
            <strong>{identity.fallback.initials}</strong>
            <em>{identity.fallback.label}</em>
          </div>
          <div>
            <ShieldCheck aria-hidden="true" />
            <span>Logo requirement</span>
            <strong>Optional</strong>
            <em>Never blocks launch.</em>
          </div>
          <div>
            <MessageCircle aria-hidden="true" />
            <span>WhatsApp contact</span>
            <strong>
              {identity.hasWhatsappNumber ? "Active" : "Optional"}
            </strong>
            <em>
              {identity.hasWhatsappNumber
                ? identity.whatsappNumber
                : "Add for public Trip Pages."}
            </em>
          </div>
          <div>
            <ShieldCheck aria-hidden="true" />
            <span>Access</span>
            <strong>{canManage ? "Owner managed" : "Read-only"}</strong>
            <em>
              {canManage
                ? "Edit assets."
                : "View only."}
            </em>
          </div>
        </section>
      </section>
    </OperationsWorkspaceShell>
  );
}

function IdentityMark({
  identity,
}: {
  identity: {
    fallback: {
      background: string;
      foreground: string;
      initials: string;
    };
    logoUrl: string;
    name: string;
  };
}) {
  if (identity.logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt=""
        aria-hidden="true"
        className="identity-preview-mark"
        src={identity.logoUrl}
      />
    );
  }

  return (
    <div
      aria-hidden="true"
      className="identity-preview-mark"
      style={{
        background: identity.fallback.background,
        color: identity.fallback.foreground,
      }}
    >
      {identity.fallback.initials}
    </div>
  );
}
