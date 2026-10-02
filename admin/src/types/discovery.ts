export type LifecycleStatus = "DRAFT" | "PUBLISHED" | "UNPUBLISHED";
export type SpiritualTradition = "HINDU" | "BUDDHIST" | "JAIN" | "SIKH" | "ISLAMIC" | "CHRISTIAN" | "OTHER" | "MULTI_TRADITION";

export interface DistrictOption { id: number; name: string; slug: string; division: string }
export interface InterestOption { id: number; name: string; slug: string; display_order: number }
export interface DiscoveryReference { districts: DistrictOption[]; interests: InterestOption[]; spiritual_traditions: SpiritualTradition[] }
export interface InterestRead { id: number; name: string; slug: string }
export interface DiscoveryFAQ { id?: number; question: string; answer: string; display_order: number; is_active: boolean }
export interface EntityMedia {
  id: number; media_asset_id: number; role: "HERO" | "GALLERY"; display_order: number; public_url: string; alt_text: string;
  specificity: "SPECIFIC" | "EDITORIAL" | "FALLBACK"; status: "ACTIVE" | "RETIRED"; creator_owner: string; source_name: string;
  source_url: string | null; usage_basis: string; attribution_text: string | null; rights_verified_at: string;
}

export interface AdminDestination {
  id: number; district_id: number; district_name: string; district_slug: string; name: string; slug: string;
  description: string | null; short_summary: string | null; image_url: string | null; image_alt: string | null; media_asset_id: number | null;
  status: LifecycleStatus; content_source: string; admin_overridden: boolean; version: number; public_path: string;
  published_at: string | null; created_at: string; updated_at: string; faqs: DiscoveryFAQ[]; media: EntityMedia[];
}
export interface AdminPlace {
  id: number; district_id: number; district_name: string; district_slug: string; destination_id: number | null; destination_name: string | null;
  name: string; slug: string; short_description: string | null; description: string | null; image_url: string | null; image_alt: string | null;
  address: string | null; opening_hours: string | null; entry_fee_info: string | null; recommended_visit_duration: string | null;
  best_time_to_visit: string | null; getting_there: string | null; nearest_railway_station: string | null; nearest_airport: string | null;
  visitor_info_source: string | null; visitor_info_source_url: string | null; visitor_info_verified_at: string | null;
  media_asset_id: number | null; interests: InterestRead[]; spiritual_tradition: SpiritualTradition | null; is_featured: boolean; display_order: number;
  status: LifecycleStatus; content_source: string; admin_overridden: boolean; version: number; public_path: string;
  published_at: string | null; created_at: string; updated_at: string; faqs: DiscoveryFAQ[]; media: EntityMedia[];
}
export interface PublicMediaAsset {
  id: number; entity_type: "DESTINATION" | "PLACE"; entity_id: number; public_url: string; content_type: string; size_bytes: number;
  width: number; height: number; alt_text: string; specificity: "SPECIFIC" | "EDITORIAL" | "FALLBACK"; creator_owner: string;
  source_name: string; source_url: string | null; usage_basis: string; attribution_text: string | null; rights_verified_at: string;
  status: "ACTIVE" | "RETIRED"; replaced_by_asset_id: number | null; created_at: string;
}

export type DestinationInput = { district_id: number; name: string; description: string | null; short_summary: string | null; faqs: DiscoveryFAQ[] };
export type PlaceInput = { district_id: number; destination_id: number | null; name: string; short_description: string | null; description: string | null; interest_ids: number[]; spiritual_tradition: SpiritualTradition | null; is_featured: boolean; display_order: number; address: string | null; opening_hours: string | null; entry_fee_info: string | null; recommended_visit_duration: string | null; best_time_to_visit: string | null; getting_there: string | null; nearest_railway_station: string | null; nearest_airport: string | null; visitor_info_source: string | null; visitor_info_source_url: string | null; visitor_info_verified_at: string | null; faqs: DiscoveryFAQ[] };
