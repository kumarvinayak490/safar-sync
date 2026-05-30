"use server";

import {
  AuthErrorPayload,
  AuthSessionPayload,
  nextRouteFromSession,
  productAuthErrorMessage,
  splitFullName,
} from "@/lib/auth-routing";
import {
  DrfRequestResult,
  authenticatedServerJsonRequest,
  setCookiesFromDrfResponse,
} from "@/lib/drf-request";

export type AuthActionState = {
  error: string;
};

export type SignupInput = {
  fullName: string;
  email: string;
  password: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type OrganizerOnboardingInput = {
  name: string;
};

export type AuthResult =
  | {
      ok: true;
      session: AuthSessionPayload;
      nextRoute: string;
    }
  | {
      ok: false;
      error: string;
    };

export async function signup(input: SignupInput): Promise<AuthResult> {
  const { firstName, lastName } = splitFullName(input.fullName);

  if (!firstName) {
    return {
      ok: false,
      error: "Enter your name so your Organizer workspace has an Owner.",
    };
  }

  return postAuthRequest("/api/auth/signup/", {
    email: input.email,
    password: input.password,
    first_name: firstName,
    last_name: lastName,
  });
}

export async function login(input: LoginInput): Promise<AuthResult> {
  return postAuthRequest("/api/auth/login/", {
    email: input.email,
    password: input.password,
  });
}

export async function createOrganizer(
  input: OrganizerOnboardingInput,
): Promise<AuthResult> {
  const name = input.name.trim();

  if (!name) {
    return { ok: false, error: "Enter the Organizer name." };
  }

  return postAuthRequest(
    "/api/onboarding/organizer/",
    { name },
    { authenticatedWrite: true },
  );
}

export async function currentSession(): Promise<AuthSessionPayload | null> {
  try {
    const result =
      await authenticatedServerJsonRequest<AuthSessionPayload>(
        "/api/auth/session/",
      );

    if (!result.response.ok) {
      return null;
    }

    return result.data;
  } catch {
    return null;
  }
}

async function postAuthRequest(
  path: string,
  body: Record<string, string>,
  options: { authenticatedWrite?: boolean } = {},
): Promise<AuthResult> {
  let result: DrfRequestResult<AuthSessionPayload>;

  try {
    result = await authenticatedServerJsonRequest<AuthSessionPayload>(path, {
      method: "POST",
      body,
      csrf: options.authenticatedWrite,
    });
  } catch {
    return {
      ok: false,
      error:
        "TripOS could not reach the local auth service. Start the API and try again.",
    };
  }

  if (!result.response.ok) {
    return {
      ok: false,
      error: productAuthErrorMessage(
        result.response.status,
        result.errorPayload as AuthErrorPayload | null,
      ),
    };
  }

  await setCookiesFromDrfResponse(result.response);
  const session = result.data as AuthSessionPayload;

  return {
    ok: true,
    session,
    nextRoute: nextRouteFromSession(session),
  };
}
