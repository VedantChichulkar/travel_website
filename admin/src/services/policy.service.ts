import { authorizedApi } from "@/services/authorized-api";
import type { HotelPolicy, HotelPolicyInput } from "@/types/hotel";

export const policyService = {
  get: (hotelId: number) => authorizedApi.get<HotelPolicy>(`/admin/hotels/${hotelId}/policy`),
  create: (hotelId: number, data: HotelPolicyInput) => authorizedApi.post<HotelPolicy, HotelPolicyInput>(`/admin/hotels/${hotelId}/policy`, data),
  update: (hotelId: number, data: HotelPolicyInput) => authorizedApi.patch<HotelPolicy, HotelPolicyInput>(`/admin/hotels/${hotelId}/policy`, data),
};
