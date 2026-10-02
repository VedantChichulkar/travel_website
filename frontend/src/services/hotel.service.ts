import { api } from "@/src/services/api";
import { hotelSearchQuery } from "@/src/lib/hotel-search";
import type { HotelDetail, HotelSearchParams, HotelSearchResponse, RoomAvailabilityResponse } from "@/src/types/hotel";

export interface PublicReview { id: number; overall_rating: number; cleanliness_rating: number; service_rating: number; location_rating: number; room_quality_rating: number; value_rating: number; review_text: string; verified_stay: boolean; created_at: string; reviewer_label: string; hotel_response: { id: number; response_text: string; created_at: string } | null; }
export interface PublicReviewList { items: PublicReview[]; total: number; average_overall_rating: number | null; }

function publicApiQuery(params: HotelSearchParams): string {
  const query = new URLSearchParams({ adults: String(params.adults), children: String(params.children), rooms: String(params.rooms), sort: params.sort });
  if (params.destination) query.set("destination", params.destination);
  else query.set("city", params.city);
  if (params.checkIn && params.checkOut) { query.set("check_in", params.checkIn); query.set("check_out", params.checkOut); }
  if (params.minPrice !== undefined) query.set("min_price", String(params.minPrice));
  if (params.maxPrice !== undefined) query.set("max_price", String(params.maxPrice));
  if (params.starRating !== undefined) query.set("star_rating", String(params.starRating));
  if (params.propertyType) query.set("property_type", params.propertyType);
  params.amenities.forEach((amenity) => query.append("amenities", amenity));
  return query.toString();
}

export const hotelService = {
  getFeaturedHotels: () => api.get<HotelSearchResponse>("/hotels?sort=recommended"),
  searchHotels: (params: HotelSearchParams) => api.get<HotelSearchResponse>(`/hotels?${publicApiQuery(params)}`),
  getHotel: (hotelRef: string | number) => api.get<HotelDetail>(`/hotels/${encodeURIComponent(hotelRef)}`),
  getReviews: (hotelRef: string | number) => api.get<PublicReviewList>(`/hotels/${encodeURIComponent(hotelRef)}/reviews`),
  getHotelRooms(hotelRef: string | number, params: HotelSearchParams) {
    const query = new URLSearchParams({ check_in: params.checkIn, check_out: params.checkOut, adults: String(params.adults), children: String(params.children), rooms: String(params.rooms) });
    return api.get<RoomAvailabilityResponse>(`/hotels/${encodeURIComponent(hotelRef)}/rooms?${query.toString()}`);
  },
  customerQuery: hotelSearchQuery,
};
