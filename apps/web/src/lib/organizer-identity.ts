import {
  drfApiUrl,
  extractDrfErrorMessage,
  multipartFormRequest
} from "./drf-request.ts";

export type OrganizerIdentityFallback = {
  initials: string;
  label: string;
  background: string;
  foreground: string;
};

export type OrganizerIdentity = {
  identityName: string;
  name: string;
  whatsappNumber: string;
  whatsappHref: string;
  hasWhatsappNumber: boolean;
  logoUrl: string;
  logoUploaded: boolean;
  fallback: OrganizerIdentityFallback;
  placeholder: boolean;
};

export type OrganizerIdentityApiPayload = {
  identity_name?: string;
  identity_whatsapp_number?: string;
  name?: string;
  logo_url?: string;
  logo_uploaded?: boolean;
  fallback?: {
    initials?: string;
    label?: string;
    background?: string;
    foreground?: string;
  };
  placeholder?: boolean;
};

export type OrganizerIdentityUpdateResult =
  | {
      ok: true;
      identity: OrganizerIdentity;
    }
  | {
      ok: false;
      message: string;
    };

const DEFAULT_FALLBACK_BACKGROUND = "oklch(0.942 0.034 252)";
const DEFAULT_FALLBACK_FOREGROUND = "oklch(0.3 0.074 258)";
const LEGACY_FALLBACK_BACKGROUND = "oklch(0.96 0.024 78)";
const LEGACY_FALLBACK_FOREGROUND = "oklch(0.36 0.08 62)";

export function normalizeOrganizerIdentity(
  payload: OrganizerIdentityApiPayload | undefined,
  fallbackName = "Organizer",
): OrganizerIdentity {
  const name = payload?.name ?? payload?.identity_name ?? fallbackName;
  const whatsappNumber = normalizeOrganizerWhatsappNumber(
    payload?.identity_whatsapp_number ?? "",
  );

  return {
    identityName: payload?.identity_name ?? name,
    name,
    whatsappNumber,
    whatsappHref: buildOrganizerWhatsappHref(whatsappNumber),
    hasWhatsappNumber: Boolean(whatsappNumber),
    logoUrl: normalizeOrganizerLogoUrl(payload?.logo_url ?? ""),
    logoUploaded: payload?.logo_uploaded ?? Boolean(payload?.logo_url),
    fallback: {
      initials: payload?.fallback?.initials ?? initials(name),
      label: payload?.fallback?.label ?? name,
      background: normalizeFallbackColor(
        payload?.fallback?.background,
        LEGACY_FALLBACK_BACKGROUND,
        DEFAULT_FALLBACK_BACKGROUND,
      ),
      foreground: normalizeFallbackColor(
        payload?.fallback?.foreground,
        LEGACY_FALLBACK_FOREGROUND,
        DEFAULT_FALLBACK_FOREGROUND,
      )
    },
    placeholder: payload?.placeholder ?? !payload?.identity_name
  };
}

function normalizeFallbackColor(
  color: string | undefined,
  legacyColor: string,
  defaultColor: string,
): string {
  return !color || color === legacyColor ? defaultColor : color;
}

export async function updateOrganizerIdentity(
  organizerId: number,
  formData: FormData,
): Promise<OrganizerIdentityUpdateResult> {
  try {
    const result = await multipartFormRequest<OrganizerIdentityApiPayload>(
      `/api/organizers/${organizerId}/identity/`,
      {
        method: "PATCH",
        formData,
        authenticated: true,
        csrf: true
      },
    );

    if (!result.response.ok || !result.data) {
      return {
        ok: false,
        message:
          extractDrfErrorMessage(result.errorPayload, [
            "identity_name",
            "identity_whatsapp_number",
            "identity_logo",
            "remove_identity_logo",
            "detail"
          ]) ?? "Organizer Identity could not be saved."
      };
    }

    return {
      ok: true,
      identity: normalizeOrganizerIdentity(result.data)
    };
  } catch {
    return {
      ok: false,
      message: "TripOS could not reach Organizer Identity. Try again after the API is running."
    };
  }
}

export function normalizeOrganizerLogoUrl(logoUrl: string): string {
  if (!logoUrl) {
    return "";
  }

  if (/^(https?:|data:|blob:)/i.test(logoUrl)) {
    return logoUrl;
  }

  if (logoUrl.startsWith("/")) {
    return drfApiUrl(logoUrl);
  }

  return logoUrl;
}

export function normalizeOrganizerWhatsappNumber(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function buildOrganizerWhatsappHref(
  whatsappNumber: string,
  message = "",
): string {
  const digits = whatsappDialDigits(whatsappNumber);
  if (!digits) {
    return "";
  }

  const query = message ? `?text=${encodeURIComponent(message)}` : "";
  return `https://wa.me/${digits}${query}`;
}

function whatsappDialDigits(whatsappNumber: string): string {
  const trimmed = whatsappNumber.trim();
  if (!trimmed) {
    return "";
  }

  let digits = trimmed.replace(/\D/g, "");
  if (!digits) {
    return "";
  }

  if (digits.startsWith("00")) {
    digits = digits.slice(2);
  } else if (digits.length === 10 && !trimmed.startsWith("+")) {
    digits = `91${digits}`;
  } else if (digits.length === 11 && digits.startsWith("0")) {
    digits = `91${digits.slice(1)}`;
  }

  return digits;
}

function initials(name: string): string {
  const value = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return value || "TO";
}
