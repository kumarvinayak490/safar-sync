import assert from "node:assert/strict";
import test from "node:test";

import {
  nextRouteFromSession,
  organizerOnboardingRedirect,
  productAuthErrorMessage,
  rootRedirectFromSession,
  splitFullName,
} from "./auth-routing.ts";

test("signup name splitting keeps first name and remaining profile name", () => {
  assert.deepEqual(splitFullName("Ananya Rao Shah"), {
    firstName: "Ananya",
    lastName: "Rao Shah",
  });
});

test("login success uses onboarding next_route from the auth session", () => {
  assert.equal(
    nextRouteFromSession({
      authenticated: true,
      user: {
        id: 1,
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "",
      },
      onboarding: {
        state: "organizer_ready",
        next_route: "/home",
        organizer: {
          id: 1,
          name: "Organizer",
          slug: "organizer",
          membership_role: "owner",
          membership_label: "Owner",
        },
        trip_count: 0,
      },
    }),
    "/home",
  );
});

test("root redirects unauthenticated users to login", () => {
  assert.equal(rootRedirectFromSession(null), "/login");
  assert.equal(
    rootRedirectFromSession({
      authenticated: false,
      user: null,
      onboarding: {
        state: "unauthenticated",
        next_route: "/login",
        organizer: null,
        trip_count: 0,
      },
    }),
    "/login",
  );
});

test("root redirects by onboarding state", () => {
  assert.equal(
    rootRedirectFromSession({
      authenticated: true,
      user: {
        id: 1,
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "",
      },
      onboarding: {
        state: "no_organizer",
        next_route: "/onboarding/organizer",
        organizer: null,
        trip_count: 0,
      },
    }),
    "/onboarding/organizer",
  );

  assert.equal(
    rootRedirectFromSession({
      authenticated: true,
      user: {
        id: 1,
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "",
      },
      onboarding: {
        state: "organizer_ready",
        next_route: "/home",
        organizer: {
          id: 1,
          name: "Organizer",
          slug: "organizer",
          membership_role: "owner",
          membership_label: "Owner",
        },
        trip_count: 0,
      },
    }),
    "/home",
  );

  assert.equal(
    rootRedirectFromSession({
      authenticated: true,
      user: {
        id: 1,
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "",
      },
      onboarding: {
        state: "organizer_ready",
        next_route: "/home",
        organizer: {
          id: 1,
          name: "Organizer",
          slug: "organizer",
          membership_role: "owner",
          membership_label: "Owner",
        },
        trip_count: 1,
      },
    }),
    "/home",
  );
});

test("organizer onboarding route allows signed-in users with no organizer", () => {
  assert.equal(
    organizerOnboardingRedirect({
      authenticated: true,
      user: {
        id: 1,
        email: "owner@example.com",
        first_name: "Owner",
        last_name: "",
      },
      onboarding: {
        state: "no_organizer",
        next_route: "/onboarding/organizer",
        organizer: null,
        trip_count: 0,
      },
    }),
    null,
  );
});

test("organizer onboarding route redirects unauthenticated and onboarded users", () => {
  assert.equal(organizerOnboardingRedirect(null), "/login");
  assert.equal(
    organizerOnboardingRedirect({
      authenticated: true,
      user: {
        id: 1,
        email: "operator@example.com",
        first_name: "Operator",
        last_name: "",
      },
      onboarding: {
        state: "organizer_ready",
        next_route: "/home",
        organizer: {
          id: 1,
          name: "Organizer",
          slug: "organizer",
          membership_role: "operator",
          membership_label: "Operator",
        },
        trip_count: 1,
      },
    }),
    "/home",
  );
});

test("invalid login error becomes product-facing copy", () => {
  assert.equal(
    productAuthErrorMessage(400, {
      non_field_errors: ["Invalid email or password."],
    }),
    "We could not sign you in with those details. Check the email and password, then try again.",
  );
});

test("duplicate signup error points the user to login", () => {
  assert.equal(
    productAuthErrorMessage(400, {
      email: ["A User with this email already exists."],
    }),
    "An account already exists for this email. Log in instead, or use another email.",
  );
});

test("organizer onboarding forbidden errors keep their product meaning", () => {
  assert.equal(
    productAuthErrorMessage(403, {
      detail:
        "Organizer onboarding is only available before your User belongs to an Organizer.",
    }),
    "Organizer onboarding is only available before your User belongs to an Organizer.",
  );
});
