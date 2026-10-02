import { authorizedApi } from "@/services/authorized-api";

export type CampaignStatus = "DRAFT" | "PAYMENT_PENDING" | "PENDING_REVIEW" | "NEEDS_CHANGES" | "SCHEDULED" | "ACTIVE" | "EXPIRED" | "REJECTED" | "PAUSED" | "CANCELLED";
export type AdvertiserType = "HOTEL" | "EXTERNAL";
export interface AdminCampaign { id: number; advertiser_type: AdvertiserType; advertiser_profile_id?: number; advertiser_name?: string; advertiser_status?: "ACTIVE" | "SUSPENDED"; hotel_name?: string; campaign_name?: string; headline?: string; short_copy?: string; target_url?: string; placement: string; plan_code: string; district_name?: string; destination_name?: string; creative_url?: string; alt_text?: string; creative_rights_confirmed: boolean; creative_source?: string; status: CampaignStatus; start_at: string; end_at: string; price_amount: string; currency: string; payment_status: string; payment_reference?: string; review_reason?: string; refund_review_required: boolean; impressions: number; clicks: number; submitted_at?: string }

export const advertisingService = {
  list: (filters: { status?: CampaignStatus; advertiser_type?: AdvertiserType; payment_status?: string; placement?: string; q?: string } = {}) => { const query = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value); }); return authorizedApi.get<AdminCampaign[]>(`/admin/advertising/campaigns${query.size ? `?${query}` : ""}`); },
  review: (id: number, action: "APPROVE" | "REQUEST_CHANGES" | "REJECT" | "PAUSE", reason?: string) => authorizedApi.post<AdminCampaign, { action: string; reason?: string }>(`/admin/advertising/campaigns/${id}/review`, { action, reason }),
  suspend: (profileId: number, suspended: boolean, reason: string) => authorizedApi.post(`/admin/advertising/advertisers/${profileId}/suspension`, { suspended, reason }),
};
