import { api } from "@/src/services/api";
import type {
  PlaceFilters,
  PublicInterestList,
  PublicPlaceDetail,
  PublicPlaceList,
} from "@/src/types/place";

function placeQuery(filters: PlaceFilters = {}) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.district) params.set("district", filters.district);
  if (filters.destination) params.set("destination", filters.destination);
  if (filters.interest) params.set("interest", filters.interest);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const placeService = {
  listInterests: () => api.get<PublicInterestList>("/interests"),
  listPlaces: (filters: PlaceFilters = {}) =>
    api.get<PublicPlaceList>(`/places${placeQuery(filters)}`),
  getPlace: (districtSlug: string, placeSlug: string) =>
    api.get<PublicPlaceDetail>(
      `/places/${encodeURIComponent(districtSlug)}/${encodeURIComponent(placeSlug)}`,
    ),
};

