import { authorizedApi } from "@/services/authorized-api";
import type { RoomType, RoomTypeInput } from "@/types/hotel";

export type RoomTypeUpdate = Partial<Omit<RoomTypeInput, "is_active">>;

export const roomService = {
  reviewQueue: (status?: string) => authorizedApi.get<RoomType[]>(`/admin/rooms/review-queue${status ? `?room_status=${status}` : ""}`),
  list: (hotelId: number) => authorizedApi.get<RoomType[]>(`/admin/hotels/${hotelId}/rooms`),
  get: (id: number) => authorizedApi.get<RoomType>(`/admin/rooms/${id}`),
  create: (hotelId: number, data: RoomTypeInput) => authorizedApi.post<RoomType, RoomTypeInput>(`/admin/hotels/${hotelId}/rooms`, data),
  update: (id: number, data: RoomTypeUpdate) => authorizedApi.patch<RoomType, RoomTypeUpdate>(`/admin/rooms/${id}`, data),
  updateStatus: (id: number, isActive: boolean) => authorizedApi.patch<RoomType, { is_active: boolean }>(`/admin/rooms/${id}/status`, { is_active: isActive }),
  review: (id: number, action: "APPROVED" | "NEEDS_CHANGES" | "BOOKABLE", reviewNotes?: string) => authorizedApi.post<RoomType, { action: string; review_notes: string | null }>(`/admin/rooms/${id}/review`, { action, review_notes: reviewNotes?.trim() || null }),
};
