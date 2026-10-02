import { authorizedApi } from "@/services/authorized-api";
import type { Amenity } from "@/types/hotel";

export interface AmenityCreate {
  name: string;
  slug: string;
  icon: string | null;
  category: string | null;
  is_active: boolean;
}

export const amenityService = {
  list: () => authorizedApi.get<Amenity[]>("/admin/amenities"),
  create: (data: AmenityCreate) => authorizedApi.post<Amenity, AmenityCreate>("/admin/amenities", data),
  assign: (hotelId: number, amenityIds: number[]) => authorizedApi.put<Amenity[], { amenity_ids: number[] }>(`/admin/hotels/${hotelId}/amenities`, { amenity_ids: amenityIds }),
};
