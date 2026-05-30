import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOrganizerWhatsappHref,
  normalizeOrganizerIdentity,
  normalizeOrganizerLogoUrl,
} from "./organizer-identity.ts";

test("organizer identity adapter keeps uploaded logo URLs stable", () => {
  const identity = normalizeOrganizerIdentity({
    identity_name: "Kaza Field Collective",
    identity_whatsapp_number: " +91 98765 43210 ",
    name: "Kaza Field Collective",
    logo_url: "/media/organizer-logos/organizer-1/logo.png",
    logo_uploaded: true,
    fallback: {
      initials: "KF",
      label: "Kaza Field Collective",
      background: "oklch(0.96 0.024 78)",
      foreground: "oklch(0.36 0.08 62)",
    },
    placeholder: false,
  });

  assert.equal(identity.name, "Kaza Field Collective");
  assert.equal(identity.whatsappNumber, "+91 98765 43210");
  assert.equal(identity.hasWhatsappNumber, true);
  assert.equal(identity.whatsappHref, "https://wa.me/919876543210");
  assert.equal(identity.logoUploaded, true);
  assert.equal(
    identity.logoUrl,
    "http://localhost:8000/media/organizer-logos/organizer-1/logo.png",
  );
  assert.equal(identity.fallback.initials, "KF");
  assert.equal(identity.fallback.background, "oklch(0.942 0.034 252)");
  assert.equal(identity.fallback.foreground, "oklch(0.3 0.074 258)");
  assert.equal(identity.placeholder, false);
});

test("organizer identity adapter provides text fallback when logo is missing", () => {
  const identity = normalizeOrganizerIdentity({
    name: "Himalayan Monsoon Cohort",
    logo_url: "",
    logo_uploaded: false,
  });

  assert.equal(identity.logoUrl, "");
  assert.equal(identity.whatsappNumber, "");
  assert.equal(identity.hasWhatsappNumber, false);
  assert.equal(identity.whatsappHref, "");
  assert.equal(identity.logoUploaded, false);
  assert.equal(identity.fallback.initials, "HM");
  assert.equal(identity.fallback.background, "oklch(0.942 0.034 252)");
  assert.equal(identity.fallback.foreground, "oklch(0.3 0.074 258)");
  assert.equal(identity.placeholder, true);
});

test("organizer WhatsApp href normalizes Indian local numbers", () => {
  assert.equal(
    buildOrganizerWhatsappHref("98765 43210", "Question about the trip"),
    "https://wa.me/919876543210?text=Question%20about%20the%20trip",
  );
});

test("organizer logo URL normalization preserves absolute URLs", () => {
  assert.equal(
    normalizeOrganizerLogoUrl("https://assets.example.com/logo.png"),
    "https://assets.example.com/logo.png",
  );
});
