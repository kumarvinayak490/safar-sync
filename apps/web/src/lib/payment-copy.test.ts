import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const guardedFiles = [
  "../app/payment-setup/page.tsx",
  "../app/payment-setup/PaymentSetupForm.tsx",
  "../app/launch/workspace-page.tsx",
  "../app/payments/workspace-page.tsx",
  "../app/trips/[organizerSlug]/[tripSlug]/page.tsx",
  "../app/trips/[organizerSlug]/[tripSlug]/PublicQrPaymentFlow.tsx",
  "./payment-setup.ts",
  "./public-trip.ts",
  "./trip-operations.ts",
  "./trip-overview.ts",
];

const blockedCopy = [
  /\boffline payments?\b/i,
  /\bmanual pay\b/i,
  /\bQR checkout\b/i,
  /\breceipts?\b/i,
  /\binvoices?\b/i,
];

test("review-gated Manual Payments copy avoids blocked public terms", async () => {
  for (const relativePath of guardedFiles) {
    const source = await readFile(
      new URL(relativePath, import.meta.url),
      "utf8",
    );

    for (const blockedPattern of blockedCopy) {
      assert.equal(
        blockedPattern.test(source),
        false,
        `${relativePath} includes blocked copy ${blockedPattern}`,
      );
    }
  }
});
