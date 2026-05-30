import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCookieHeader,
  extractDrfErrorMessage,
  multipartFormRequest,
  parseSetCookie,
  publicJsonRequest,
  splitSetCookieHeader
} from "./drf-request.ts";

test("public JSON requests centralize base URL, headers, body serialization, and parsing", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  let requestedInit: RequestInit | undefined;

  globalThis.fetch = async (url, init) => {
    requestedUrl = String(url);
    requestedInit = init;
    return Response.json({ id: 42 }, { status: 201 });
  };

  try {
    const result = await publicJsonRequest<{ id: number }>("/api/public/example/", {
      method: "POST",
      body: { trip: "Spiti" }
    });

    assert.equal(requestedUrl, "http://localhost:8000/api/public/example/");
    assert.equal(requestedInit?.method, "POST");
    assert.equal((requestedInit?.headers as Record<string, string>)?.Accept, "application/json");
    assert.equal(
      (requestedInit?.headers as Record<string, string>)?.["Content-Type"],
      "application/json"
    );
    assert.equal(requestedInit?.body, JSON.stringify({ trip: "Spiti" }));
    assert.equal(result.response.status, 201);
    assert.deepEqual(result.data, { id: 42 });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("multipart requests avoid overriding the browser-generated form boundary", async () => {
  const originalFetch = globalThis.fetch;
  let requestedInit: RequestInit | undefined;
  const formData = new FormData();
  formData.append("amount_inr", "8000");

  globalThis.fetch = async (_url, init) => {
    requestedInit = init;
    return Response.json({}, { status: 200 });
  };

  try {
    const result = await multipartFormRequest("/api/portal/token/manual-payments/", {
      formData
    });

    assert.equal(requestedInit?.method, "POST");
    assert.equal((requestedInit?.headers as Record<string, string>)?.Accept, "application/json");
    assert.equal(
      (requestedInit?.headers as Record<string, string>)?.["Content-Type"],
      undefined
    );
    assert.equal(requestedInit?.body, formData);
    assert.equal(result.response.ok, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("DRF error extraction finds the first useful nested field message", () => {
  assert.equal(
    extractDrfErrorMessage(
      {
        detail: "Permission denied.",
        packages: [{ reservation_amount_inr: ["Reservation Amount is required."] }]
      },
      ["packages", "detail"]
    ),
    "Reservation Amount is required."
  );
});

test("cookie helpers preserve forwarded cookies and split combined set-cookie headers", () => {
  assert.equal(
    buildCookieHeader([
      { name: "sessionid", value: "abc" },
      { name: "csrftoken", value: "def" }
    ]),
    "sessionid=abc; csrftoken=def"
  );

  const split = splitSetCookieHeader(
    "sessionid=abc; Path=/; HttpOnly; SameSite=Lax, csrftoken=def; Path=/; Expires=Wed, 21 Oct 2026 07:28:00 GMT"
  );

  assert.equal(split.length, 2);
  assert.equal(parseSetCookie(split[0])?.name, "sessionid");
  assert.deepEqual(parseSetCookie(split[0])?.options, {
    path: "/",
    httpOnly: true,
    sameSite: "lax"
  });
  assert.equal(parseSetCookie(split[1])?.name, "csrftoken");
});
