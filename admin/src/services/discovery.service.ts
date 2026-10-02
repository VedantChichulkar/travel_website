import { authorizedApi } from "@/services/authorized-api";
import type { AdminDestination, AdminPlace, DestinationInput, DiscoveryReference, LifecycleStatus, PlaceInput, PublicMediaAsset } from "@/types/discovery";

function query(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
  return params.size ? `?${params}` : "";
}

export const discoveryService = {
  reference: () => authorizedApi.get<DiscoveryReference>("/admin/discovery/reference"),
  destinations: (values: { query?: string; lifecycle?: LifecycleStatus; district_id?: number } = {}) => authorizedApi.get<{items: AdminDestination[]; total: number}>(`/admin/discovery/destinations${query(values)}`),
  destination: (id: number) => authorizedApi.get<AdminDestination>(`/admin/discovery/destinations/${id}`),
  createDestination: (body: DestinationInput) => authorizedApi.post<AdminDestination, DestinationInput>("/admin/discovery/destinations", body),
  updateDestination: (id: number, body: Partial<DestinationInput> & {expected_version: number}) => authorizedApi.patch<AdminDestination, typeof body>(`/admin/discovery/destinations/${id}`, body),
  destinationsForDistrict: async (districtId: number) => (await authorizedApi.get<{items: AdminDestination[]; total: number}>(`/admin/discovery/destinations${query({district_id: districtId})}`)).items,
  places: (values: { query?: string; lifecycle?: LifecycleStatus; district_id?: number; destination_id?: number; interest_id?: number } = {}) => authorizedApi.get<{items: AdminPlace[]; total: number}>(`/admin/discovery/places${query(values)}`),
  place: (id: number) => authorizedApi.get<AdminPlace>(`/admin/discovery/places/${id}`),
  createPlace: (body: PlaceInput) => authorizedApi.post<AdminPlace, PlaceInput>("/admin/discovery/places", body),
  updatePlace: (id: number, body: Partial<PlaceInput> & {expected_version: number}) => authorizedApi.patch<AdminPlace, typeof body>(`/admin/discovery/places/${id}`, body),
  publish: <T>(kind: "destinations" | "places", id: number, version: number, reason: string) => authorizedApi.post<{entity: T; affected: Record<string, number>}, {expected_version: number; reason: string}>(`/admin/discovery/${kind}/${id}/publish`, {expected_version: version, reason}),
  unpublish: <T>(kind: "destinations" | "places", id: number, version: number, reason: string) => authorizedApi.post<{entity: T; affected: Record<string, number>}, {expected_version: number; reason: string}>(`/admin/discovery/${kind}/${id}/unpublish`, {expected_version: version, reason}),
  media: (status?: "ACTIVE" | "RETIRED") => authorizedApi.get<PublicMediaAsset[]>(`/admin/discovery/media${query({status_value: status})}`),
  uploadMedia: (entityType: "DESTINATION" | "PLACE", entityId: number, body: FormData) => authorizedApi.post<PublicMediaAsset, FormData>(`/admin/discovery/media/${entityType}/${entityId}`, body),
  updateMedia: <T>(entityType: "DESTINATION" | "PLACE", entityId: number, relationId: number, body: {expected_version: number; role: "HERO" | "GALLERY"; display_order: number; alt_text: string}) => authorizedApi.patch<T, typeof body>(`/admin/discovery/media/${entityType}/${entityId}/${relationId}`, body),
  retireMedia: <T>(entityType: "DESTINATION" | "PLACE", entityId: number, relationId: number, version: number) => authorizedApi.delete<T>(`/admin/discovery/media/${entityType}/${entityId}/${relationId}?expected_version=${version}`),
};
