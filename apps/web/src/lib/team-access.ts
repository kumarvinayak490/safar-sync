import {
  authenticatedServerJsonRequest,
  extractDrfErrorMessage
} from "@/lib/drf-request";

export type OrganizerRole = "owner" | "operator";

export type TeamAccessUser = {
  id: number;
  email: string;
  name: string;
  firstName: string;
  lastName: string;
};

export type OrganizerMembershipSummary = {
  id: number;
  role: OrganizerRole;
  roleLabel: string;
  user: TeamAccessUser;
  createdAt: string;
};

export type OrganizerInvitationSummary = {
  id: number;
  email: string;
  role: OrganizerRole;
  roleLabel: string;
  status: "pending" | "accepted" | "revoked";
  statusLabel: string;
  token?: string;
  inviteUrlPath?: string;
  lastSentAt?: string;
  resendCount?: number;
  createdAt?: string;
  organizer?: {
    id: number;
    name: string;
    slug: string;
  };
};

export type TeamAccess = {
  memberships: OrganizerMembershipSummary[];
  pendingInvitations: OrganizerInvitationSummary[];
  ownerCount: number;
};

export type TeamAccessResult =
  | { ok: true; teamAccess: TeamAccess }
  | { ok: false; status: "unauthenticated" | "forbidden" | "unreachable"; message: string };

export type InvitationResult =
  | { ok: true; invitation: OrganizerInvitationSummary }
  | { ok: false; message: string };

export type InvitationAcceptResult =
  | { ok: true; invitation: OrganizerInvitationSummary }
  | { ok: false; status: "unauthenticated" | "invalid" | "unreachable"; message: string };

export async function getTeamAccess(organizerId: number): Promise<TeamAccessResult> {
  try {
    const result = await authenticatedServerJsonRequest<TeamAccessApiPayload>(
      `/api/organizers/${organizerId}/team-access/`
    );

    if (result.response.status === 401) {
      return {
        ok: false,
        status: "unauthenticated",
        message: "Log in to view Team Access."
      };
    }

    if (result.response.status === 403) {
      return {
        ok: false,
        status: "forbidden",
        message: "Your User cannot view Team Access for this Organizer."
      };
    }

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        status: "unreachable",
        message: "Team Access is not available."
      };
    }

    return {
      ok: true,
      teamAccess: normalizeTeamAccess(result.data)
    };
  } catch {
    return {
      ok: false,
      status: "unreachable",
      message: "TripOS could not reach Team Access. Try again after the API is running."
    };
  }
}

export async function createOrganizerInvitation(
  organizerId: number,
  input: {
    email: string;
    role?: OrganizerRole;
    confirmOwnerPowers?: boolean;
  }
): Promise<InvitationResult> {
  return invitationMutation(`/api/organizers/${organizerId}/team-access/`, {
    email: input.email,
    role: input.role ?? "operator",
    confirm_owner_powers: input.confirmOwnerPowers ?? false
  });
}

export async function resendOrganizerInvitation(
  organizerId: number,
  invitationId: number
): Promise<InvitationResult> {
  return invitationMutation(
    `/api/organizers/${organizerId}/team-access/invitations/${invitationId}/resend/`,
    {}
  );
}

export async function revokeOrganizerInvitation(
  organizerId: number,
  invitationId: number
): Promise<InvitationResult> {
  return invitationMutation(
    `/api/organizers/${organizerId}/team-access/invitations/${invitationId}/revoke/`,
    {}
  );
}

export async function getOrganizerInvitation(
  token: string
): Promise<InvitationAcceptResult> {
  try {
    const result = await authenticatedServerJsonRequest<InvitationApiPayload>(
      `/api/organizer-invitations/${token}/`,
      { method: "GET" }
    );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        status: "invalid",
        message:
          extractDrfErrorMessage(result.errorPayload, ["detail"]) ??
          "Organizer Invitation was not found."
      };
    }

    return { ok: true, invitation: normalizeInvitation(result.data) };
  } catch {
    return {
      ok: false,
      status: "unreachable",
      message: "TripOS could not reach this Organizer Invitation."
    };
  }
}

export async function acceptOrganizerInvitation(
  token: string
): Promise<InvitationAcceptResult> {
  try {
    const result = await authenticatedServerJsonRequest<{
      invitation?: InvitationApiPayload;
    }>(`/api/organizer-invitations/${token}/`, {
      method: "POST",
      body: {},
      csrf: true
    });

    if (result.response.status === 401) {
      return {
        ok: false,
        status: "unauthenticated",
        message: "Log in or create your User before accepting."
      };
    }

    if (!result.response.ok || !result.data?.invitation) {
      return {
        ok: false,
        status: "invalid",
        message:
          extractDrfErrorMessage(result.errorPayload, ["detail"]) ??
          "This Organizer Invitation could not be accepted."
      };
    }

    return {
      ok: true,
      invitation: normalizeInvitation(result.data.invitation)
    };
  } catch {
    return {
      ok: false,
      status: "unreachable",
      message: "TripOS could not accept this Organizer Invitation."
    };
  }
}

async function invitationMutation(
  path: string,
  body: Record<string, unknown>
): Promise<InvitationResult> {
  try {
    const result = await authenticatedServerJsonRequest<InvitationApiPayload>(path, {
      method: "POST",
      body,
      csrf: true
    });

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, [
            "email",
            "role",
            "confirm_owner_powers",
            "detail"
          ]) ?? "Organizer Invitation could not be saved."
      };
    }

    return {
      ok: true,
      invitation: normalizeInvitation(result.data)
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach Team Access. Try again after the API is running."
    };
  }
}

export function normalizeTeamAccess(payload: TeamAccessApiPayload): TeamAccess {
  return {
    memberships: payload.memberships?.map(normalizeMembership) ?? [],
    pendingInvitations:
      payload.pending_invitations?.map(normalizeInvitation) ?? [],
    ownerCount: payload.owner_count ?? 0
  };
}

function normalizeMembership(payload: MembershipApiPayload): OrganizerMembershipSummary {
  return {
    id: payload.id ?? 0,
    role: normalizeRole(payload.role),
    roleLabel: payload.role_label ?? roleLabel(normalizeRole(payload.role)),
    user: {
      id: payload.user?.id ?? 0,
      email: payload.user?.email ?? "",
      name: payload.user?.name ?? payload.user?.email ?? "User",
      firstName: payload.user?.first_name ?? "",
      lastName: payload.user?.last_name ?? ""
    },
    createdAt: payload.created_at ?? ""
  };
}

function normalizeInvitation(payload: InvitationApiPayload): OrganizerInvitationSummary {
  const role = normalizeRole(payload.role);

  return {
    id: payload.id ?? 0,
    email: payload.email ?? "",
    role,
    roleLabel: payload.role_label ?? roleLabel(role),
    status: normalizeStatus(payload.status),
    statusLabel: payload.status_label ?? "Pending",
    token: payload.token,
    inviteUrlPath: payload.invite_url_path,
    lastSentAt: payload.last_sent_at,
    resendCount: payload.resend_count ?? 0,
    createdAt: payload.created_at,
    organizer: payload.organizer
      ? {
          id: payload.organizer.id ?? 0,
          name: payload.organizer.name ?? "Organizer",
          slug: payload.organizer.slug ?? "organizer"
        }
      : undefined
  };
}

function normalizeRole(role: unknown): OrganizerRole {
  return role === "owner" ? "owner" : "operator";
}

function normalizeStatus(status: unknown): "pending" | "accepted" | "revoked" {
  if (status === "accepted" || status === "revoked") {
    return status;
  }
  return "pending";
}

function roleLabel(role: OrganizerRole): string {
  return role === "owner" ? "Owner" : "Operator";
}

type TeamAccessApiPayload = {
  memberships?: MembershipApiPayload[];
  pending_invitations?: InvitationApiPayload[];
  owner_count?: number;
};

type MembershipApiPayload = {
  id?: number;
  role?: string;
  role_label?: string;
  user?: {
    id?: number;
    email?: string;
    name?: string;
    first_name?: string;
    last_name?: string;
  };
  created_at?: string;
};

type InvitationApiPayload = {
  id?: number;
  email?: string;
  role?: string;
  role_label?: string;
  status?: string;
  status_label?: string;
  token?: string;
  invite_url_path?: string;
  last_sent_at?: string;
  resend_count?: number;
  created_at?: string;
  organizer?: {
    id?: number;
    name?: string;
    slug?: string;
  };
};
