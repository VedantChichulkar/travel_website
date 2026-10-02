import { api } from "@/src/services/api";
import type { DestinationSearchResponse, PublicDestinationDetail, PublicDestinationList, PublicDistrictDetail, PublicDistrictList } from "@/src/types/destination";

export const destinationService = {
  listDistricts: (query?: string) => api.get<PublicDistrictList>(`/destinations${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  getDistrict: (districtSlug: string) => api.get<PublicDistrictDetail>(`/destinations/${encodeURIComponent(districtSlug)}`),
  listPlaces: (districtSlug: string) => api.get<PublicDestinationList>(`/destinations/${encodeURIComponent(districtSlug)}/places`),
  getPlace: (districtSlug: string, destinationSlug: string) => api.get<PublicDestinationDetail>(`/destinations/${encodeURIComponent(districtSlug)}/${encodeURIComponent(destinationSlug)}`),
  search: (query: string, limit = 8, includePlaces = false, includeStories = false) => api.get<DestinationSearchResponse>(`/destinations/search?q=${encodeURIComponent(query)}&limit=${limit}${includePlaces ? "&include_places=true" : ""}${includeStories ? "&include_stories=true" : ""}`),
};
