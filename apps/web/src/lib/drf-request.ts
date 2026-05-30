import { extractDrfErrorMessage } from "./drf-error.ts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export { extractDrfErrorMessage };

export type DrfErrorPayload = Record<string, unknown> | string | unknown[] | null;

export type DrfRequestResult<T> = {
  response: Response;
  data: T | null;
  errorPayload: DrfErrorPayload;
  errorMessage: string | null;
};

type DrfJsonRequestOptions = {
  method?: string;
  body?: unknown;
  csrf?: boolean;
  headers?: HeadersInit;
  cache?: RequestCache;
};

type DrfMultipartRequestOptions = {
  method?: string;
  formData: FormData;
  authenticated?: boolean;
  csrf?: boolean;
  headers?: HeadersInit;
  cache?: RequestCache;
};

export function drfApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export async function authenticatedServerJsonRequest<T>(
  path: string,
  options: DrfJsonRequestOptions = {}
): Promise<DrfRequestResult<T>> {
  return drfJsonRequest<T>(path, {
    ...options,
    authenticated: true
  });
}

export async function publicJsonRequest<T>(
  path: string,
  options: DrfJsonRequestOptions = {}
): Promise<DrfRequestResult<T>> {
  return drfJsonRequest<T>(path, {
    ...options,
    authenticated: false
  });
}

export async function multipartFormRequest<T>(
  path: string,
  options: DrfMultipartRequestOptions
): Promise<DrfRequestResult<T>> {
  const response = await fetch(drfApiUrl(path), {
    method: options.method ?? "POST",
    cache: options.cache ?? "no-store",
    headers: {
      Accept: "application/json",
      ...(options.authenticated ? await forwardedCookieHeader() : {}),
      ...(options.csrf ? await forwardedCsrfHeader() : {}),
      ...options.headers
    },
    body: options.formData
  });

  return parseDrfResponse<T>(response);
}

export async function parseDrfResponse<T>(
  response: Response
): Promise<DrfRequestResult<T>> {
  const payload = await parseJson(response);

  return {
    response,
    data: response.ok ? (payload as T) : null,
    errorPayload: response.ok ? null : (payload as DrfErrorPayload),
    errorMessage: response.ok ? null : extractDrfErrorMessage(payload)
  };
}

export async function setCookiesFromDrfResponse(response: Response): Promise<void> {
  const cookieStore = await serverCookies();

  for (const setCookie of setCookieHeaders(response.headers)) {
    const parsedCookie = parseSetCookie(setCookie);
    if (!parsedCookie) {
      continue;
    }

    cookieStore.set(parsedCookie.name, parsedCookie.value, parsedCookie.options);
  }
}

export function buildCookieHeader(cookiePairs: Array<{ name: string; value: string }>): string {
  return cookiePairs.map(({ name, value }) => `${name}=${value}`).join("; ");
}

export function splitSetCookieHeader(header: string): string[] {
  return header.split(/,(?=\s*[^;,]+=)/).map((cookie) => cookie.trim());
}

export function parseSetCookie(setCookie: string) {
  const [nameValue, ...attributes] = setCookie.split(";").map((part) => part.trim());
  const separatorIndex = nameValue.indexOf("=");
  if (separatorIndex < 1) {
    return null;
  }

  const options: {
    path?: string;
    httpOnly?: boolean;
    secure?: boolean;
    sameSite?: "lax" | "strict" | "none";
    expires?: Date;
    maxAge?: number;
  } = {
    path: "/"
  };

  for (const attribute of attributes) {
    const [rawName, rawValue = ""] = attribute.split("=");
    const name = rawName.toLowerCase();
    const value = rawValue.trim();

    if (name === "path" && value) {
      options.path = value;
    } else if (name === "httponly") {
      options.httpOnly = true;
    } else if (name === "secure") {
      options.secure = true;
    } else if (name === "samesite") {
      const sameSite = value.toLowerCase();
      if (sameSite === "lax" || sameSite === "strict" || sameSite === "none") {
        options.sameSite = sameSite;
      }
    } else if (name === "expires" && value) {
      options.expires = new Date(value);
    } else if (name === "max-age" && value) {
      options.maxAge = Number(value);
    }
  }

  return {
    name: nameValue.slice(0, separatorIndex),
    value: nameValue.slice(separatorIndex + 1),
    options
  };
}

async function drfJsonRequest<T>(
  path: string,
  options: DrfJsonRequestOptions & { authenticated: boolean }
): Promise<DrfRequestResult<T>> {
  const response = await fetch(drfApiUrl(path), {
    method: options.method ?? (options.body === undefined ? "GET" : "POST"),
    cache: options.cache ?? "no-store",
    headers: {
      Accept: "application/json",
      ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(options.authenticated ? await forwardedCookieHeader() : {}),
      ...(options.csrf ? await forwardedCsrfHeader() : {}),
      ...options.headers
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });

  return parseDrfResponse<T>(response);
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
}

async function forwardedCookieHeader(): Promise<HeadersInit> {
  const cookie = buildCookieHeader((await serverCookies()).getAll());
  return cookie ? { Cookie: cookie } : {};
}

async function forwardedCsrfHeader(): Promise<HeadersInit> {
  const token = (await serverCookies()).get("csrftoken")?.value;
  return token ? { "X-CSRFToken": token } : {};
}

async function serverCookies() {
  const { cookies } = await import("next/headers");
  return cookies();
}

function setCookieHeaders(headers: Headers): string[] {
  const headersWithGetSetCookie = headers as Headers & {
    getSetCookie?: () => string[];
  };
  const setCookies = headersWithGetSetCookie.getSetCookie?.();
  if (setCookies?.length) {
    return setCookies;
  }

  const setCookieHeader = headers.get("set-cookie");
  return setCookieHeader ? splitSetCookieHeader(setCookieHeader) : [];
}
