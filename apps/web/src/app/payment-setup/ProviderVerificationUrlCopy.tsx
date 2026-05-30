"use client";

import { Clipboard, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { ProviderVerificationUrl } from "@/lib/payment-setup";

type ProviderVerificationUrlCopyProps = {
  providerVerificationUrl: ProviderVerificationUrl;
};

export function ProviderVerificationUrlCopy({
  providerVerificationUrl,
}: ProviderVerificationUrlCopyProps) {
  const [origin, setOrigin] = useState("");
  const [copied, setCopied] = useState(false);
  const urlPath = providerVerificationUrl.urlPath;
  const displayUrl = useMemo(() => {
    if (!urlPath) {
      return "";
    }
    return origin ? `${origin}${urlPath}` : urlPath;
  }, [origin, urlPath]);

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  async function copyUrl() {
    if (!displayUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(displayUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="provider-verification-url-copy">
      <input
        aria-label="Provider Verification URL"
        readOnly
        type="text"
        value={displayUrl || "Publish a Public Trip Page first"}
        onFocus={(event) => event.currentTarget.select()}
      />
      <div className="provider-verification-url-actions">
        {providerVerificationUrl.available ? (
          <>
            <button className="icon-link" type="button" onClick={copyUrl}>
              <Clipboard aria-hidden="true" />
              {copied ? "Copied" : "Copy"}
            </button>
            <a className="icon-link" href={urlPath}>
              <ExternalLink aria-hidden="true" />
              View
            </a>
          </>
        ) : null}
      </div>
    </div>
  );
}
