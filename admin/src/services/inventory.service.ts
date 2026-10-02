import { authorizedApi } from "@/services/authorized-api";
import type { RoomInventory, RoomInventoryInput } from "@/types/hotel";

export type InventoryUpdate = Partial<Omit<RoomInventoryInput, "inventory_date">>;

export const inventoryService = {
  list(roomId: number, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    const query = params.size ? `?${params.toString()}` : "";
    return authorizedApi.get<RoomInventory[]>(`/admin/rooms/${roomId}/inventory${query}`);
  },
  create: (roomId: number, data: RoomInventoryInput) => authorizedApi.post<RoomInventory, RoomInventoryInput>(`/admin/rooms/${roomId}/inventory`, data),
  update: (id: number, data: InventoryUpdate) => authorizedApi.patch<RoomInventory, InventoryUpdate>(`/admin/inventory/${id}`, data),
};
