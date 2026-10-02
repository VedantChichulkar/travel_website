import { authorizedApi } from "@/services/authorized-api";
import type { Hotel, HotelCreate, HotelDetail, HotelImage, HotelUpdate } from "@/types/hotel";
import type { BookingGatewayStatus } from "@/types/hotel";

export const hotelService = {
  list: (query = "") => authorizedApi.get<Hotel[]>(`/admin/hotels${query}`),
  get: (id: number) => authorizedApi.get<HotelDetail>(`/admin/hotels/${id}`),
  create: (data: HotelCreate) => authorizedApi.post<Hotel, HotelCreate>("/admin/hotels", data),
  update: (id: number, data: HotelUpdate) => authorizedApi.patch<Hotel, HotelUpdate>(`/admin/hotels/${id}`, data),
  getGateway: (id: number) => authorizedApi.get<{ hotel_id: number; partner_requested_status: BookingGatewayStatus; effective_status: BookingGatewayStatus; override_status: BookingGatewayStatus | null; override_reason: string | null; inventory_is_fresh: boolean; verified: boolean }>(`/admin/hotels/${id}/booking-gateway`),
  overrideGateway: (id: number, booking_gateway_status: BookingGatewayStatus, reason: string) => authorizedApi.put(`/admin/hotels/${id}/booking-gateway/override`, { booking_gateway_status, reason }),
  clearGatewayOverride: (id: number, reason: string) => authorizedApi.delete(`/admin/hotels/${id}/booking-gateway/override?reason=${encodeURIComponent(reason)}`),
  addImage: (id: number, data: { image_url: string; alt_text: string | null; is_cover: boolean; display_order: number }) =>
    authorizedApi.post<HotelImage, typeof data>(`/admin/hotels/${id}/images`, data),
  removeImage: (hotelId: number, imageId: number) => authorizedApi.delete(`/admin/hotels/${hotelId}/images/${imageId}`),
  reviewRoom: (roomId: number, action: "APPROVED" | "NEEDS_CHANGES" | "BOOKABLE", reviewNotes?: string | null) =>
    authorizedApi.post(`/admin/rooms/${roomId}/review`, { action, review_notes: reviewNotes ?? null }),
};
