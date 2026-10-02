import type { Safari } from "@/src/types/safari";

export const SAFARI_IMAGES = {
  hero: "/images/safaris/tiger-forest-hero.webp",
  leopard: "/images/safaris/leopard-rocky-forest.webp",
  deer: "/images/safaris/chital-forest-clearing.webp",
  birdlife: "/images/safaris/peacock-forest-lake.webp",
  biodiversity: "/images/safaris/biodiversity-wetland-bg.webp",
  wildlifeStory: "/images/safaris/wildlife-story-forest-bg.webp",
  safariJourney: "/images/safaris/safari-vehicle-landscape.webp",
} as const;

const editorialFallbacks = [SAFARI_IMAGES.hero, SAFARI_IMAGES.leopard, SAFARI_IMAGES.deer, SAFARI_IMAGES.birdlife] as const;

/**
 * The current Safari API does not expose reserve-specific media. Keep the
 * fallback choice centralized and deterministic so cards never fetch random
 * remote imagery or imply that an editorial image was photographed there.
 */
export function safariImageFor(safari?: Pick<Safari, "id" | "slug">) {
  if (!safari) return SAFARI_IMAGES.hero;
  const seed = `${safari.id}:${safari.slug}`.split("").reduce((total, value) => total + value.charCodeAt(0), 0);
  return editorialFallbacks[seed % editorialFallbacks.length];
}

export const SAFARI_IMAGE_ALT = "Representative Maharashtra wildlife and forest landscape";
