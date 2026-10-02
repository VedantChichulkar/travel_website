"use client";

/* eslint-disable @next/next/no-img-element -- remote discovery assets use the manifest's future CDN origin and cannot be constrained to a build-time host allowlist */

import Image from "next/image";
import { useState } from "react";

import type { ResolvedDiscoveryMedia } from "@/src/lib/discovery-media";

export function DiscoveryMediaImage({
  media,
  priority = false,
  sizes = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw",
  className = "",
}: {
  media: ResolvedDiscoveryMedia;
  priority?: boolean;
  sizes?: string;
  className?: string;
}) {
  const [failed, setFailed] = useState<"primary" | "fallback" | null>(null);
  const active = failed === "primary" && media.fallback
    ? { src: media.fallback.src, alt: media.fallback.alt }
    : { src: media.src, alt: media.alt };

  if (failed === "fallback" || (failed === "primary" && !media.fallback)) {
    return <div className={`destination-image-fallback grid h-full w-full place-items-center ${className}`} role="img" aria-label="Discovery artwork is temporarily unavailable"><span className="text-5xl font-black text-[var(--brand)]/25" aria-hidden>M</span></div>;
  }

  if (active.src.startsWith("/")) {
    return (
      <Image
        src={active.src}
        alt={active.alt}
        fill
        unoptimized={media.status !== "SPECIFIC"}
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        sizes={sizes}
        className={`object-cover ${className}`}
        onError={() => setFailed(failed === "primary" ? "fallback" : "primary")}
      />
    );
  }

  return <img src={active.src} alt={active.alt} loading={priority ? "eager" : "lazy"} fetchPriority={priority ? "high" : "auto"} referrerPolicy="no-referrer" className={`h-full w-full object-cover ${className}`} onError={() => setFailed(failed === "primary" ? "fallback" : "primary")} />;
}
