"use client";

/* eslint-disable @next/next/no-img-element -- customer media URLs are supplied by the existing backend workflows */

import { useState } from "react";

function usablePublicUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (value.startsWith("/")) return value;

  try {
    const parsed = new URL(value);
    if (parsed.protocol === "https:") return value;
    if (process.env.NODE_ENV === "development" && parsed.protocol === "http:") return value;
  } catch {
    return null;
  }

  return null;
}

export function MediaImage({
  src,
  alt,
  className = "",
  eager = false,
  fallback,
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  eager?: boolean;
  fallback: React.ReactNode;
}) {
  const safeSrc = usablePublicUrl(src);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (!safeSrc || failedSrc === safeSrc) return fallback;

  return (
    <img
      src={safeSrc}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={eager ? "high" : "auto"}
      referrerPolicy="no-referrer"
      onError={() => setFailedSrc(safeSrc)}
      className={className}
    />
  );
}
