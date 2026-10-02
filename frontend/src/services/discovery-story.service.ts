import { api } from "@/src/services/api";
import type { DiscoveryStoryFilters, PublicDiscoveryStoryDetail, PublicDiscoveryStoryList } from "@/src/types/discovery-story";


function queryString(filters: DiscoveryStoryFilters = {}) {
  const params = new URLSearchParams();
  if (filters.interest) params.set("interest", filters.interest);
  if (filters.district) params.set("district", filters.district);
  if (filters.q) params.set("q", filters.q);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();
  return query ? `?${query}` : "";
}


export const discoveryStoryService = {
  listStories: (filters: DiscoveryStoryFilters = {}) =>
    api.get<PublicDiscoveryStoryList>(`/discovery-stories${queryString(filters)}`),
  getStory: (slug: string) =>
    api.get<PublicDiscoveryStoryDetail>(`/discovery-stories/${encodeURIComponent(slug)}`),
};
