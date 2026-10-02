import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type { AdvertiserProfile, AdvertisingConfig, Campaign, PublicAdList } from "@/src/types/advertising";
import type { PaymentOrder } from "@/src/services/booking.service";

function token() { const value = tokenStorage.getTokens()?.accessToken; if (!value) throw new Error("Not authenticated"); return value; }

export const advertisingService = {
  config: () => api.get<AdvertisingConfig>("/partner/advertising/config", token()),
  list: () => api.get<Campaign[]>("/partner/advertising/campaigns", token()),
  create: (body: { plan_code: string; start_at: string; district_slug?: string; destination_slug?: string; alt_text?: string }) => api.post<Campaign, typeof body>("/partner/advertising/campaigns", body, token()),
  upload: (id: number, file: File, altText: string) => { const body = new FormData(); body.set("file", file); body.set("alt_text", altText); return api.post<Campaign, FormData>(`/partner/advertising/campaigns/${id}/creative`, body, token()); },
  pay: (id: number) => api.post<PaymentOrder, Record<string, never>>(`/partner/advertising/campaigns/${id}/payment-order`, {}, token()),
  submit: (id: number) => api.post<Campaign, Record<string, never>>(`/partner/advertising/campaigns/${id}/submit`, {}, token()),
  publicAds: (placement: string, district?: string, destination?: string) => { const q = new URLSearchParams({ placement }); if (district) q.set("district_slug", district); if (destination) q.set("destination_slug", destination); return api.get<PublicAdList>(`/ads?${q}`); },
  event: (id: string, kind: "impressions" | "clicks", eventId: string) => api.post<{ recorded: boolean }, { event_id: string }>(`/ads/${id}/${kind}`, { event_id: eventId }),
  advertiserProfile: () => api.get<AdvertiserProfile>("/advertiser/profile", token()),
  saveAdvertiserProfile: (body: { business_name: string; contact_person: string; business_email: string; phone: string; category: string; description?: string; website?: string }) => api.put<AdvertiserProfile, typeof body>("/advertiser/profile", body, token()),
  advertiserConfig: () => api.get<AdvertisingConfig>("/advertiser/config", token()),
  advertiserCampaigns: () => api.get<Campaign[]>("/advertiser/campaigns", token()),
  createExternal: (body: { campaign_name: string; headline: string; short_copy: string; target_url: string; plan_code: string; start_at: string; district_slug?: string; destination_slug?: string; alt_text?: string; creative_rights_confirmed: boolean; creative_source?: string }) => api.post<Campaign, typeof body>("/advertiser/campaigns", body, token()),
  updateExternal: (id: number, body: { campaign_name?: string; headline?: string; short_copy?: string; target_url?: string; alt_text?: string; creative_rights_confirmed?: boolean; creative_source?: string; version: number }) => api.patch<Campaign, typeof body>(`/advertiser/campaigns/${id}`, body, token()),
  uploadExternal: (id: number, file: File, altText: string, source: string) => { const body = new FormData(); body.set("file", file); body.set("alt_text", altText); body.set("rights_confirmed", "true"); body.set("source", source); return api.post<Campaign, FormData>(`/advertiser/campaigns/${id}/creative`, body, token()); },
  payExternal: (id: number) => api.post<PaymentOrder, Record<string, never>>(`/advertiser/campaigns/${id}/payment-order`, {}, token()),
  submitExternal: (id: number) => api.post<Campaign, Record<string, never>>(`/advertiser/campaigns/${id}/submit`, {}, token()),
};
