import type { Metadata } from "next";
import Link from "next/link";

import { OperationsWorkspaceShell } from "@/app/OperationsWorkspaceShell";
import { loadWorkspace } from "@/app/workspace";
import { canCreateTrips } from "@/lib/operations-workspace";

import { createTripAction } from "./actions";
import { TripDraftCreationForm } from "./TripDraftCreationForm";

export const metadata: Metadata = {
  title: "Create Trip | TripOS",
  description: "Create a draft paid Trip from Trips management",
};

export default async function NewTripPage() {
  const workspace = await loadWorkspace();
  const organizer = workspace.organizer;
  const isOwner = canCreateTrips(workspace);

  return (
    <OperationsWorkspaceShell
      activePath="/trips"
      currentPath="/trips/new"
      workspace={workspace}
    >
      <section
        className="workspace-section trip-creation-section"
        aria-labelledby="trip-title"
      >
        <div className="workspace-heading trip-creation-heading">
          <div>
            <p className="eyebrow">Trips</p>
            <h2 id="trip-title">Create Trip</h2>
            <p className="workspace-heading-copy">
              Draft first. Overview next.
            </p>
          </div>
          <Link className="secondary-link-button" href="/trips">
            Back to Trips
          </Link>
        </div>

        {isOwner ? (
          <TripDraftCreationForm
            action={createTripAction}
            organizerId={organizer.id}
            organizerName={organizer.name}
          />
        ) : (
          <div className="empty-state standalone" role="status">
            <span>Owner action required</span>
            <strong>Operators cannot create Trips</strong>
            <p>Ask an Owner to create the Trip.</p>
          </div>
        )}
      </section>
    </OperationsWorkspaceShell>
  );
}
