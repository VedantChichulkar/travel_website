import { resolveInterestMedia } from "@/src/lib/discovery-media";

export type KnownInterestSlug =
  | "sacred-spiritual"
  | "ancient-caves"
  | "forts-heritage"
  | "history-architecture"
  | "nature-hills"
  | "wildlife-forests"
  | "beaches-coast"
  | "culture-traditions"
  | "food-local-flavours";

export interface InterestVisual {
  shortTitle: string;
  eyebrow: string;
  description: string;
  image: string;
  imageAlt: string;
  objectPosition?: string;
  related: readonly KnownInterestSlug[];
}

type InterestVisualCopy = Omit<InterestVisual, "image" | "imageAlt">;

const INTEREST_VISUAL_COPY: Record<KnownInterestSlug, InterestVisualCopy> = {
  "sacred-spiritual": {
    shortTitle: "Sacred & Spiritual",
    eyebrow: "Faith, architecture & place",
    description: "Explore sacred places across Maharashtra’s districts and traditions with care and context.",
    related: ["ancient-caves", "history-architecture", "culture-traditions"],
  },
  "ancient-caves": {
    shortTitle: "Ancient Caves",
    eyebrow: "Rock-cut heritage",
    description: "Discover cave architecture and the landscapes that hold Maharashtra’s rock-cut heritage.",
    related: ["history-architecture", "sacred-spiritual", "forts-heritage"],
  },
  "forts-heritage": {
    shortTitle: "Forts & Heritage",
    eyebrow: "Strongholds in the landscape",
    description: "Follow hill forts, coastal defences and historic precincts through their home districts.",
    related: ["history-architecture", "nature-hills", "beaches-coast"],
  },
  "history-architecture": {
    shortTitle: "History & Architecture",
    eyebrow: "Built stories",
    description: "Browse monuments, historic architecture and enduring urban heritage by location.",
    related: ["forts-heritage", "ancient-caves", "culture-traditions"],
  },
  "nature-hills": {
    shortTitle: "Nature & Hill Escapes",
    eyebrow: "Sahyadri air",
    description: "Find hill landscapes, waterfalls, lakes and quieter routes through Maharashtra’s highlands.",
    related: ["wildlife-forests", "forts-heritage", "beaches-coast"],
  },
  "wildlife-forests": {
    shortTitle: "Wildlife & Forests",
    eyebrow: "Forests & habitats",
    description: "Explore wildlife landscapes while keeping Safari availability and booking in its managed flow.",
    objectPosition: "65% center",
    related: ["nature-hills", "beaches-coast", "culture-traditions"],
  },
  "beaches-coast": {
    shortTitle: "Beaches & Coast",
    eyebrow: "The Konkan edge",
    description: "Travel through beaches, sea forts and coastal districts shaped by the Arabian Sea.",
    related: ["forts-heritage", "nature-hills", "food-local-flavours"],
  },
  "culture-traditions": {
    shortTitle: "Culture & Traditions",
    eyebrow: "Living craft & expression",
    description: "Meet regional craft, textile, performance and community traditions through the places they belong.",
    related: ["food-local-flavours", "sacred-spiritual", "history-architecture"],
  },
  "food-local-flavours": {
    shortTitle: "Food & Local Flavours",
    eyebrow: "Regional tables",
    description: "Use local foodways as cultural context for deciding where to travel next.",
    related: ["culture-traditions", "beaches-coast", "nature-hills"],
  },
};

export const KNOWN_INTEREST_SLUGS = Object.keys(INTEREST_VISUAL_COPY) as KnownInterestSlug[];

export function interestVisual(slug: string): InterestVisual | undefined {
  const copy = INTEREST_VISUAL_COPY[slug as KnownInterestSlug];
  if (!copy) return undefined;
  const media = resolveInterestMedia(slug);
  return { ...copy, image: media.src, imageAlt: media.alt };
}

export const SPIRITUAL_TRADITION_LABELS = {
  HINDU: "Hindu",
  BUDDHIST: "Buddhist",
  JAIN: "Jain",
  SIKH: "Sikh",
  ISLAMIC: "Islamic",
  CHRISTIAN: "Christian",
  OTHER: "Other tradition",
  MULTI_TRADITION: "Multi-tradition",
} as const;
