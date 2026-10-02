import { authorizedApi } from "@/services/authorized-api";

export type SettlementStatus = "ON_HOLD" | "ELIGIBLE" | "PROCESSING" | "SETTLED" | "RECONCILIATION_REQUIRED";
export type PayoutStatus = "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED" | "RECONCILIATION_REQUIRED" | "REVERSED";
export interface SettlementEvent { id: number; old_status: SettlementStatus | null; new_status: SettlementStatus; note: string; actor_user_id: number | null; created_at: string; }
export interface SettlementRecord {
  id: number; hotel_id: number; booking_id: number; currency: string; gross_amount: string; commission_rate: string | null; commission_rule: string | null; vayora_fee: string; refund_deductions: string; adjustment_total: string; net_payable: string;
  eligibility_date: string; status: SettlementStatus; hold_reason: string | null; payout_provider: string | null; payout_provider_reference: string | null; processing_at: string | null; settled_at: string | null; created_at: string;
  booking: { id: number; booking_reference: string; check_in: string; check_out: string; checked_out_at: string | null; status: string; payment_status: string; payments: Array<{ id: number; amount: string; currency: string; status: string; reconciliation_status: string }>; cancellation: { cancellation_type: string; status: string; refundable_amount: string; refunded_amount: string; requires_manual_review: boolean; refunds: Array<{ id: number; amount: string; status: string }> } | null }; hotel: { id: number; name: string }; adjustments: Array<{ id: number; kind: string; amount: string; reason: string; applies_to_current_settlement: boolean; applied_to_settlement_id: number | null; applied_at: string | null; created_at: string }>; events: SettlementEvent[];
  payout: { id: number; provider: string; provider_payout_id: string | null; provider_status: string | null; provider_utr: string | null; status: PayoutStatus; amount: string; currency: string; attempts: number; failure_reason: string | null; reconciliation_reason: string | null; initiated_at: string | null; completed_at: string | null } | null;
}

export const settlementService = {
  list: (status?: SettlementStatus) => authorizedApi.get<SettlementRecord[]>(`/admin/settlements${status ? `?settlement_status=${status}` : ""}`),
  refresh: (reason: string) => authorizedApi.post<SettlementRecord[], { reason: string }>("/admin/settlements/refresh", { reason }),
  hold: (id: number, reason: string) => authorizedApi.post<SettlementRecord, { reason: string }>(`/admin/settlements/${id}/hold`, { reason }),
  release: (id: number, reason: string) => authorizedApi.post<SettlementRecord, { reason: string }>(`/admin/settlements/${id}/release`, { reason }),
  process: (id: number, reason: string) => authorizedApi.post<SettlementRecord, { reason: string }>(`/admin/settlements/${id}/process`, { reason }),
  reconcile: (id: number, reason: string) => authorizedApi.post<SettlementRecord, { reason: string }>(`/admin/settlements/${id}/reconcile`, { reason }),
  retry: (id: number, reason: string) => authorizedApi.post<SettlementRecord, { reason: string }>(`/admin/settlements/${id}/retry`, { reason }),
  adjust: (id: number, kind: "ADJUSTMENT" | "REVERSAL", amount: string, reason: string) => authorizedApi.post<SettlementRecord, { kind: "ADJUSTMENT" | "REVERSAL"; amount: string; reason: string }>(`/admin/settlements/${id}/adjustments`, { kind, amount, reason }),
};
