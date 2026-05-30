import { extractDrfErrorMessage } from "./drf-error.ts";

export type AuthErrorPayload = {
  detail?: unknown;
  non_field_errors?: unknown;
  name?: unknown;
  identity_name?: unknown;
  identity_logo?: unknown;
  email?: unknown;
  password?: unknown;
  first_name?: unknown;
  last_name?: unknown;
};

export type AuthSessionPayload = {
  authenticated: boolean;
  user: null | {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  onboarding: {
    state: string;
    next_route: string;
    organizer: null | {
      id: number;
      name: string;
      slug: string;
      membership_role: string;
      membership_label: string;
    };
    trip_count: number;
  };
};

export function nextRouteFromSession(payload: AuthSessionPayload): string {
  const nextRoute = payload.onboarding?.next_route;

  if (typeof nextRoute === "string" && nextRoute.startsWith("/")) {
    return nextRoute;
  }

  if (!payload.authenticated) {
    return "/login";
  }

  return "/onboarding/organizer";
}

export function rootRedirectFromSession(
  payload: AuthSessionPayload | null,
): string {
  if (!payload?.authenticated) {
    return "/login";
  }

  return nextRouteFromSession(payload);
}

export function organizerOnboardingRedirect(
  payload: AuthSessionPayload | null,
): string | null {
  if (!payload?.authenticated) {
    return "/login";
  }

  if (payload.onboarding?.state === "no_organizer") {
    return null;
  }

  return nextRouteFromSession(payload);
}

export function splitFullName(fullName: string): {
  firstName: string;
  lastName: string;
} {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  const [firstName = "", ...remaining] = parts;

  return {
    firstName,
    lastName: remaining.join(" "),
  };
}

export function productAuthErrorMessage(
  status: number,
  payload: AuthErrorPayload | null,
): string {
  const firstMessage = extractDrfErrorMessage(payload, [
    "non_field_errors",
    "detail",
    "name",
    "identity_name",
    "identity_logo",
    "email",
    "password",
    "first_name",
    "last_name",
  ]);

  if (status === 400 && firstMessage) {
    return normalizeKnownMessage(firstMessage);
  }

  if (status === 401 || status === 403) {
    const detail = extractDrfErrorMessage(payload?.detail);
    if (detail?.toLowerCase().includes("organizer onboarding")) {
      return detail;
    }

    return "We could not sign you in with those details. Check the email and password, then try again.";
  }

  if (status >= 500) {
    return "TripOS could not reach the local auth service. Try again after the API is running.";
  }

  return "TripOS could not complete this request. Check the details and try again.";
}

function normalizeKnownMessage(message: string): string {
  if (message.toLowerCase().includes("invalid email or password")) {
    return "We could not sign you in with those details. Check the email and password, then try again.";
  }

  if (message.toLowerCase().includes("already exists")) {
    return "An account already exists for this email. Log in instead, or use another email.";
  }

  return message;
}
