export const PROPERTY_TYPES = ["HOTEL", "RESORT", "VILLA", "APARTMENT", "HOSTEL", "HOMESTAY"] as const;
export const HOTEL_SORTS = ["recommended", "price_asc", "price_desc", "rating"] as const;
export const BOOKING_GATEWAY_STATUSES = ["ACTIVE", "BOOKING_ON_REQUEST", "PAUSED"] as const;

export type PropertyType = (typeof PROPERTY_TYPES)[number];
export type HotelSort = (typeof HOTEL_SORTS)[number];
export type BookingGatewayStatus = (typeof BOOKING_GATEWAY_STATUSES)[number];

export interface Amenity {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  category: string | null;
}

export interface HotelImage {
  id: number;
  image_url: string;
  alt_text: string | null;
  is_cover: boolean;
  display_order: number;
}

export interface HotelPolicy {
  cancellation_policy: string | null;
  children_policy: string | null;
  pet_policy: string | null;
  smoking_policy: string | null;
  extra_bed_policy: string | null;
  additional_rules: string | null;
}

export interface HotelSearchParams {
  city: string;
  destination?: string;
  district?: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  rooms: number;
  minPrice?: number;
  maxPrice?: number;
  starRating?: number;
  propertyType?: PropertyType;
  amenities: string[];
  sort: HotelSort;
}

export interface Hotel {
  id: number;
  name: string;
  slug: string;
  property_type: PropertyType;
  star_rating: string;
  city: string;
  district?: string | null;
  district_slug?: string | null;
  destination_slug?: string | null;
  state: string;
  country: string;
  is_featured: boolean;
  cover_image_url: string | null;
  amenities: Amenity[];
  starting_price: string | null;
  currency: string | null;
  is_available: boolean;
  booking_mode: BookingGatewayStatus;
  booking_enabled: boolean;
  last_inventory_update: string | null;
}

export interface RoomAvailability {
  id: number;
  hotel_id: number;
  name: string;
  description: string | null;
  max_adults: number;
  max_children: number;
  max_guests: number;
  bed_type: string;
  bed_count: number;
  room_size_sqm: number | null;
  currency: string;
  images: HotelImage[];
  available_rooms: number;
  nights: number;
  price_per_night: string;
  estimated_total: string;
  nightly_prices: { inventory_date: string; price: string }[];
}

export interface HotelDetail extends Hotel {
  description: string | null;
  address_line1: string;
  address_line2: string | null;
  postal_code: string;
  latitude: number | null;
  longitude: number | null;
  check_in_time: string;
  check_out_time: string;
  images: HotelImage[];
  policy: HotelPolicy | null;
}

export interface HotelSearchResult {
  items: Hotel[];
  total: number;
}

export interface RoomAvailabilityResponse {
  hotel_id: number;
  check_in: string;
  check_out: string;
  adults: number;
  children: number;
  rooms: number;
  booking_mode: BookingGatewayStatus;
  booking_enabled: boolean;
  last_inventory_update: string | null;
  items: RoomAvailability[];
}

export type HotelSearchResponse = HotelSearchResult;
