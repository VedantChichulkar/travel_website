import type { PublicInterest, PublicPlace } from "@/src/types/place";

export interface PublicStoryDistrict {
  name: string;
  slug: string;
  path: string;
}

export interface PublicStoryDestination {
  name: string;
  slug: string;
  district_name: string;
  district_slug: string;
  path: string;
}

export interface PublicDiscoveryStory {
  title: string;
  slug: string;
  short_description: string;
  image_url: string | null;
  is_featured: boolean;
  interests: PublicInterest[];
  districts: PublicStoryDistrict[];
  path: string;
}

export interface PublicDiscoveryStoryDetail extends PublicDiscoveryStory {
  body: string;
  destinations: PublicStoryDestination[];
  related_places: PublicPlace[];
}

export interface PublicDiscoveryStoryList {
  items: PublicDiscoveryStory[];
  total: number;
}

export interface DiscoveryStoryFilters {
  interest?: string;
  district?: string;
  q?: string;
  limit?: number;
}
