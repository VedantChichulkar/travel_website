import Image from "next/image";

import { SAFARI_IMAGE_ALT, safariImageFor } from "@/src/lib/safari-images";
import type { Safari } from "@/src/types/safari";

export function SafariArtwork({
  safari,
  variant = "card",
  priority = false,
  alt = SAFARI_IMAGE_ALT,
  className = "",
}: {
  safari?: Pick<Safari, "id" | "slug">;
  variant?: "card" | "hero" | "feature";
  priority?: boolean;
  alt?: string;
  className?: string;
}) {
  const positioning = variant === "hero" ? "absolute inset-0 min-h-full" : "relative";
  const sizing = variant === "feature" ? "min-h-80" : variant === "card" ? "aspect-[4/3]" : "";
  return <div className={`${positioning} overflow-hidden bg-[#10251c] ${sizing} ${className}`}>
    <Image
      src={safariImageFor(safari)}
      alt={alt}
      fill
      loading={priority ? "eager" : "lazy"}
      sizes={variant === "hero" ? "100vw" : variant === "feature" ? "(max-width: 768px) 100vw, 60vw" : "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"}
      className="object-cover transition-transform duration-700 motion-reduce:transition-none group-hover:scale-[1.025]"
    />
    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" aria-hidden="true" />
  </div>;
}
