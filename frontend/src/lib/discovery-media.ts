import manifestJson from "@/src/data/discovery-media-manifest.json";
import type { PublicDiscoveryStory } from "@/src/types/discovery-story";
import type { PublicPlace } from "@/src/types/place";

export type DiscoveryMediaStatus = "SPECIFIC" | "EDITORIAL" | "FALLBACK";

type Provenance = {
  source: string;
  creator: string;
  usageBasis: string;
  license: string;
  attributionText: string | null;
  sourceUrl: string | null;
  documentary: boolean;
};

type AssetRecord = {
  asset: string;
  status: DiscoveryMediaStatus;
  mediaType: string;
  provenanceId: string;
  alt: string;
};

type EntityRecord = {
  status: DiscoveryMediaStatus;
  fallbackInterest: string;
  priorityTier?: 1 | 2 | 3;
  asset?: string;
  alt?: string;
  provenanceId?: string;
};

type DiscoveryMediaManifest = {
  version: number;
  verifiedDate: string;
  provenance: Record<string, Provenance>;
  globalFallback: AssetRecord;
  interests: Record<string, AssetRecord>;
  places: Record<string, EntityRecord>;
  stories: Record<string, EntityRecord>;
};

const manifest = manifestJson as unknown as DiscoveryMediaManifest;

export type ResolvedDiscoveryMedia = {
  src: string;
  alt: string;
  status: DiscoveryMediaStatus;
  documentary: boolean;
  provenance: Provenance;
  fallback: { src: string; alt: string } | null;
};

function provenanceFor(record: AssetRecord | EntityRecord): Provenance {
  const id = record.provenanceId;
  return (id && manifest.provenance[id]) || manifest.provenance[manifest.globalFallback.provenanceId];
}

function globalFallback(): ResolvedDiscoveryMedia {
  const record = manifest.globalFallback;
  return {
    src: record.asset,
    alt: record.alt,
    status: "FALLBACK",
    documentary: false,
    provenance: provenanceFor(record),
    fallback: null,
  };
}

export function resolveInterestMedia(interestSlug: string): ResolvedDiscoveryMedia {
  const record = manifest.interests[interestSlug];
  if (!record) return globalFallback();
  return {
    src: record.asset,
    alt: record.alt,
    status: record.status,
    documentary: provenanceFor(record).documentary,
    provenance: provenanceFor(record),
    fallback: { src: manifest.globalFallback.asset, alt: manifest.globalFallback.alt },
  };
}

function categoryFallback(interestSlug: string | undefined, entityName: string): ResolvedDiscoveryMedia {
  const record = interestSlug ? manifest.interests[interestSlug] : undefined;
  if (!record) {
    const global = globalFallback();
    return { ...global, alt: `${global.alt}; used as a fallback for ${entityName}` };
  }
  return {
    src: record.asset,
    alt: `${record.alt}; used as a category fallback for ${entityName} and does not depict the subject`,
    status: "FALLBACK",
    documentary: false,
    provenance: provenanceFor(record),
    fallback: { src: manifest.globalFallback.asset, alt: `${manifest.globalFallback.alt}; used as a fallback for ${entityName}` },
  };
}

export function resolvePlaceMedia(place: PublicPlace): ResolvedDiscoveryMedia {
  if (place.image_url && place.image_alt && place.image_status) {
    const fallback = categoryFallback(place.interests[0]?.slug, place.name);
    return {
      src: place.image_url,
      alt: place.image_alt,
      status: place.image_status,
      documentary: place.image_status === "SPECIFIC",
      provenance: {
        source: "Maharashtra Tourist Places public media registry",
        creator: "Rights metadata available to Maharashtra Tourist Places administrators",
        usageBasis: "Verified before publication",
        license: "Recorded in the Maharashtra Tourist Places rights registry",
        attributionText: null,
        sourceUrl: null,
        documentary: place.image_status === "SPECIFIC",
      },
      fallback,
    };
  }
  const key = `${place.district.slug}/${place.slug}`;
  const record = manifest.places[key];
  if (record?.status === "SPECIFIC" && record.asset && record.alt && record.provenanceId) {
    return {
      src: record.asset,
      alt: record.alt,
      status: "SPECIFIC",
      documentary: provenanceFor(record).documentary,
      provenance: provenanceFor(record),
      fallback: categoryFallback(record.fallbackInterest, place.name),
    };
  }
  return categoryFallback(record?.fallbackInterest || place.interests[0]?.slug, place.name);
}

export function resolveStoryMedia(story: PublicDiscoveryStory): ResolvedDiscoveryMedia {
  const record = manifest.stories[story.slug];
  if (record?.status === "SPECIFIC" && record.asset && record.alt && record.provenanceId) {
    return {
      src: record.asset,
      alt: record.alt,
      status: "SPECIFIC",
      documentary: provenanceFor(record).documentary,
      provenance: provenanceFor(record),
      fallback: categoryFallback(record.fallbackInterest, story.title),
    };
  }
  return categoryFallback(record?.fallbackInterest || story.interests[0]?.slug, story.title);
}

export function discoveryMediaManifest(): Readonly<DiscoveryMediaManifest> {
  return manifest;
}
