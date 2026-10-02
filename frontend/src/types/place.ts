export type SpiritualTradition =
  | "HINDU"
  | "BUDDHIST"
  | "JAIN"
  | "SIKH"
  | "ISLAMIC"
  | "CHRISTIAN"
  | "OTHER"
  | "MULTI_TRADITION";

export interface PublicInterest {
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
  path: string;
}

export interface PublicInterestList {
  items: PublicInterest[];
  total: number;
}

export interface PublicPlaceLocation {
  name: string;
  slug: string;
  path: string;
}

export interface PublicFAQ { id: number; question: string; answer: string; display_order: number }
export interface PublicDiscoveryMedia { id: number; media_asset_id: number; public_url: string; alt_text: string; specificity: "SPECIFIC" | "EDITORIAL" | "FALLBACK"; role: "HERO" | "GALLERY"; display_order: number; attribution_text: string | null; source_name: string }

export interface PublicPlace {
  name: string;
  slug: string;
  short_description: string | null;
  image_url: string | null;
  image_alt: string | null;
  image_status: "SPECIFIC" | "EDITORIAL" | "FALLBACK" | null;
  is_featured: boolean;
  district: PublicPlaceLocation;
  destination: PublicPlaceLocation | null;
  interests: PublicInterest[];
  path: string;
}

export interface PublicPlaceDetail extends PublicPlace {
  description: string | null;
  spiritual_tradition: SpiritualTradition | null;
  address: string | null;
  opening_hours: string | null;
  entry_fee_info: string | null;
  recommended_visit_duration: string | null;
  best_time_to_visit: string | null;
  getting_there: string | null;
  nearest_railway_station: string | null;
  nearest_airport: string | null;
  visitor_info_source: string | null;
  visitor_info_source_url: string | null;
  visitor_info_verified_at: string | null;
  gallery: PublicDiscoveryMedia[];
  faqs: PublicFAQ[];
  related_places: PublicPlace[];
}

export interface PublicPlaceList {
  items: PublicPlace[];
  total: number;
  limit: number;
  offset: number;
}

export interface PlaceFilters {
  q?: string;
  district?: string;
  destination?: string;
  interest?: string;
  limit?: number;
  offset?: number;
}
