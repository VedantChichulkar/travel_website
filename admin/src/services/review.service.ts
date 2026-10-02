import { authorizedApi } from "@/services/authorized-api";

export interface AdminReview {
  id: number; booking_id: number; hotel_id: number; overall_rating: number; cleanliness_rating: number; service_rating: number; location_rating: number; room_quality_rating: number; value_rating: number; review_text: string; verified_stay: boolean; moderation_status: "PUBLISHED" | "PENDING_REVIEW" | "REJECTED"; risk_level: "NORMAL" | "HIGH"; risk_reasons: string[]; created_at: string;
  hotel: { id: number; name: string }; booking: { id: number; booking_reference: string; checked_out_at: string | null }; hotel_response: { id: number; response_text: string; created_at: string } | null; challenge: { id: number; reason: string; details: string; status: "OPEN" | "UPHELD" | "DISMISSED"; resolution_note: string | null; created_at: string; resolved_at: string | null } | null; moderation_events: Array<{ id: number; old_status: string | null; new_status: string; note: string; actor_user_id: number | null; created_at: string }>;
}

export const reviewService = {
  queue: () => authorizedApi.get<AdminReview[]>("/admin/reviews/moderation"),
  moderate: (id: number, action: "PUBLISH" | "REJECT", note: string) => authorizedApi.post<AdminReview, { action: "PUBLISH" | "REJECT"; note: string }>(`/admin/reviews/${id}/moderate`, { action, note }),
};
