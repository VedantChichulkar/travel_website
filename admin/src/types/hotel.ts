export const PROPERTY_TYPES = ["HOTEL", "RESORT", "HOSTEL", "APARTMENT", "VILLA", "HOMESTAY"] as const;
export const HOTEL_STATUSES = ["DRAFT", "PENDING", "ACTIVE", "INACTIVE", "SUSPENDED"] as const;
export const BOOKING_GATEWAY_STATUSES = ["ACTIVE", "BOOKING_ON_REQUEST", "PAUSED"] as const;

export type PropertyType = (typeof PROPERTY_TYPES)[number];
export type HotelStatus = (typeof HOTEL_STATUSES)[number];
export type BookingGatewayStatus = (typeof BOOKING_GATEWAY_STATUSES)[number];

export interface HotelImage {
  id: number;
  hotel_id: number;
  image_url: string;
  alt_text: string | null;
  is_cover: boolean;
  display_order: number;
  created_at: string;
}

export interface Amenity {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  category: string | null;
  is_active: boolean;
}

export interface HotelPolicyInput {
  cancellation_policy: string | null;
  children_policy: string | null;
  pet_policy: string | null;
  smoking_policy: string | null;
  extra_bed_policy: string | null;
  additional_rules: string | null;
}

export interface HotelPolicy extends HotelPolicyInput {
  id: number;
  hotel_id: number;
  created_at: string;
  updated_at: string;
}

export interface RoomImage {
  id: number;
  room_type_id: number;
  image_url: string;
  alt_text: string | null;
  is_cover: boolean;
  display_order: number;
  created_at: string;
}

export interface RoomTypeInput {
  name: string;
  description: string | null;
  max_adults: number;
  max_children: number;
  max_guests: number;
  bed_type: string;
  bed_count: number;
  room_size_sqm: number | null;
  base_price: number;
  currency: string;
  total_rooms: number;
  is_active: boolean;
}

export interface RoomType extends RoomTypeInput {
  id: number;
  hotel_id: number;
  status?: "DRAFT" | "PENDING" | "APPROVED" | "NEEDS_CHANGES" | "BOOKABLE";
  review_notes?: string | null;
  created_at: string;
  updated_at: string;
  images: RoomImage[];
}

export interface RoomInventoryInput {
  inventory_date: string;
  total_inventory: number;
  blocked_inventory: number;
  price: number;
  is_closed: boolean;
  available_inventory?: number;
}

export interface RoomInventory extends Omit<RoomInventoryInput, "available_inventory"> {
  id: number;
  room_type_id: number;
  available_inventory: number;
  confirmed_inventory: number;
  held_inventory: number;
  created_at: string;
  updated_at: string;
}

export interface HotelInput {
  name: string;
  slug: string;
  description: string | null;
  property_type: PropertyType;
  star_rating: number;
  address_line1: string;
  address_line2: string | null;
  city: string;
  district?: string | null;
  state: string;
  country: string;
  postal_code: string;
  latitude: number | null;
  longitude: number | null;
  contact_email: string | null;
  contact_phone: string | null;
  check_in_time: string;
  check_out_time: string;
  is_featured: boolean;
  booking_gateway_status?: BookingGatewayStatus;
}

export type HotelCreate = HotelInput;
export type HotelUpdate = Partial<HotelInput>;

export interface Hotel extends HotelInput {
  id: number;
  status: HotelStatus;
  booking_gateway_status: BookingGatewayStatus;
  created_at: string;
  updated_at: string;
}

export interface HotelDetail extends Hotel {
  images: HotelImage[];
  amenities: Amenity[];
  policy: HotelPolicy | null;
  room_types: RoomType[];
}
