import { authorizedApi } from "@/services/authorized-api";
import { tokenStorage } from "@/services/token-storage";

export type VerificationStatus = "PENDING" | "APPROVED" | "REJECTED" | "ADDITIONAL_INFO_REQUIRED" | "NEEDS_CHANGES";
export type PaymentStatus = "NOT_STARTED" | "PENDING" | "PAID" | "FAILED" | "REFUND_PENDING" | "REFUNDED";
export type BusinessType = "PROPRIETORSHIP" | "PARTNERSHIP" | "PRIVATE_LIMITED" | "PUBLIC_LIMITED" | "LLP" | "OTHER";

// ─── List view ─────────────────────────────────────────────────────────────────
export interface VerificationListItem {
  id: number;
  hotel_id: number;
  hotel_name: string;
  hotel_slug: string;
  hotel_city: string;
  hotel_state: string;
  partner_id: number | null;
  partner_name: string | null;
  partner_email: string | null;
  business_name: string;
  business_type: BusinessType;
  verification_status: VerificationStatus;
  payment_status: PaymentStatus;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
}

// ─── Verification record (matches HotelVerificationResponse schema) ─────────────
export interface VerificationRecord {
  id: number;
  hotel_id: number;
  business_name: string;
  business_type: BusinessType;
  gstin: string | null;
  pan: string | null;
  bank_account_number: string | null;
  bank_ifsc: string | null;
  bank_name: string | null;
  bank_beneficiary_name: string | null;
  document_proof_type: string | null;
  document_available: boolean;
  verification_status: VerificationStatus;
  rejection_reason: string | null;
  admin_notes: string | null;
  reviewed_by: number | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  fee: {
    amount: string; currency: string; payment_status: PaymentStatus; payment_id: number | null;
    provider_order_id: string | null; payment_reference: string | null; paid_at: string | null;
    refund_status: string | null; refund_id: number | null; refund_reference: string | null;
    refund_failure_reason: string | null; disclaimer: string;
  } | null;
}

// ─── Hotel summary (subset of HotelResponse) ──────────────────────────────────
export interface HotelSummary {
  id: number;
  name: string;
  slug: string;
  property_type: string;
  status: string;
  booking_gateway_status: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  district?: string | null;
  state: string;
  postal_code: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  check_in_time: string;
  check_out_time: string;
  partner_id: number | null;
}

// ─── Detail response (matches AdminVerificationDetailResponse schema) ──────────
export interface VerificationDetail {
  verification: VerificationRecord;
  hotel: HotelSummary;
  /** Backend returns dict | None. Shape: {id, full_name, email, phone, created_at} */
  partner: Record<string, string | number | null> | null;
}

export const verificationService = {
  list(status?: VerificationStatus): Promise<VerificationListItem[]> {
    const query = status ? `?status=${status}` : "";
    return authorizedApi.get<VerificationListItem[]>(`/admin/verifications${query}`);
  },

  getDetail(id: number): Promise<VerificationDetail> {
    return authorizedApi.get<VerificationDetail>(`/admin/verifications/${id}`);
  },

  async downloadDocument(id: number): Promise<void> {
    const token = tokenStorage.get()?.accessToken;
    if (!token) throw new Error("Not authenticated");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/verifications/${id}/document`, { headers: { Authorization: `Bearer ${token}` }, credentials: "include" });
    if (!response.ok) throw new Error("Document download failed");
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "verification-document"; anchor.click(); URL.revokeObjectURL(url);
  },

  approve(id: number, notes?: string): Promise<VerificationRecord> {
    const params = notes ? `?notes=${encodeURIComponent(notes)}` : "";
    return authorizedApi.post<VerificationRecord, Record<string, never>>(
      `/admin/verifications/${id}/approve${params}`,
      {}
    );
  },

  reject(id: number, reason: string, notes?: string): Promise<VerificationRecord> {
    const params = new URLSearchParams({ reason });
    if (notes) params.set("notes", notes);
    return authorizedApi.post<VerificationRecord, Record<string, never>>(
      `/admin/verifications/${id}/reject?${params.toString()}`,
      {}
    );
  },

  requestInfo(id: number, notes: string): Promise<VerificationRecord> {
    return authorizedApi.post<VerificationRecord, Record<string, never>>(
      `/admin/verifications/${id}/request-info?notes=${encodeURIComponent(notes)}`,
      {}
    );
  },

  requestChanges(id: number, reason: string): Promise<VerificationRecord> {
    return authorizedApi.post<VerificationRecord, Record<string, never>>(
      `/admin/verifications/${id}/request-changes?reason=${encodeURIComponent(reason)}`,
      {}
    );
  },
};
