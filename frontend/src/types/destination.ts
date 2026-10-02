export interface PublicDistrict {
  name: string;
  slug: string;
  division: string;
  short_description: string | null;
  hero_image_url: string | null;
  path: string;
}

export interface PublicDistrictList {
  items: PublicDistrict[];
  total: number;
}

export interface PublicDestination {
  name: string;
  slug: string;
  description: string | null;
  short_summary: string | null;
  image_url: string | null;
  image_alt: string | null;
  image_status: "SPECIFIC" | "EDITORIAL" | "FALLBACK" | null;
  district_name: string;
  district_slug: string;
  path: string;
}

export interface PublicDestinationDetail extends PublicDestination {
  gallery: PublicDiscoveryMedia[];
  faqs: PublicFAQ[];
  places: PublicPlace[];
}

export interface PublicDestinationList {
  items: PublicDestination[];
  total: number;
}

export interface PublicDistrictDetail extends PublicDistrict {
  destinations: PublicDestination[];
}

export interface DestinationSearchResult {
  kind: "DISTRICT" | "DESTINATION" | "PLACE" | "STORY";
  name: string;
  slug: string;
  district_name: string | null;
  district_slug: string | null;
  destination_name: string | null;
  destination_slug: string | null;
  path: string;
}

export interface DestinationSearchResponse {
  items: DestinationSearchResult[];
  total: number;
}
import type { PublicDiscoveryMedia, PublicFAQ, PublicPlace } from "@/src/types/place";
