import { redirect } from "next/navigation";

import { loadTripWorkspace } from "@/app/workspace";

type TripWorkspaceRootPageProps = {
  params: {
    tripId: string;
  };
};

export default async function TripWorkspaceRootPage({
  params,
}: TripWorkspaceRootPageProps) {
  await loadTripWorkspace({ tripId: params.tripId, section: "overview" });
  redirect(`/operations/trips/${params.tripId}/overview`);
}
