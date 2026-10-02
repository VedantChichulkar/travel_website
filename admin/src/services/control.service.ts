import { authorizedApi } from "@/services/authorized-api";
import type { Hotel, HotelStatus } from "@/types/hotel";

export interface Overview { users: Record<string, number>; hotels: Record<string, number>; bookings: Record<string, number>; finance: Record<string, number>; governance: Record<string, number>; }
export interface AdminUser { id: number; full_name: string; masked_email: string; masked_phone: string; role: string; status: string; is_active: boolean; is_email_verified: boolean; is_phone_verified: boolean; created_at: string; }
export interface AdminBooking { id: number; booking_reference: string; customer_id: number; hotel_id: number; hotel_name: string; status: string; payment_status: string; check_in: string; check_out: string; rooms: number; currency: string; total_amount: string; created_at: string; }
export interface AdminPayment { id: number; booking_id: number; provider: string; provider_order_id: string; provider_payment_id: string | null; amount: string; currency: string; status: string; reconciliation_status: string; failure_reason: string | null; verified_at: string | null; reconciliation_attempts: number; reconciliation_next_retry_at: string | null; reconciliation_reason: string | null; created_at: string; }
export interface AdminPaymentDetail { payment: AdminPayment & { receipt_status: string }; booking_id: number; booking_reference: string; booking_status: string; customer_id: number; customer_name: string; hotel_id: number; hotel_name: string; room_type_id: number; room_name: string; expected_amount: string; expected_currency: string; hold_token: string | null; hold_status: string | null; hold_expires_at: string | null; created_at: string; updated_at: string; }
export interface AdminCancellation { id: number; booking_id: number; cancellation_type: string; status: string; reason: string; refundable_amount: string; refunded_amount: string; requires_manual_review: boolean; created_at: string; }
export interface AdminRefund { id: number; cancellation_id: number | null; verification_id: number | null; safari_request_id: number | null; payment_id: number; amount: string; currency: string; status: string; provider: string; provider_refund_id: string | null; provider_status: string | null; failure_reason: string | null; reconciliation_reason: string | null; execution_attempts: number; next_retry_at: string | null; completed_at: string | null; created_at: string; }
export interface AdminRefundDetail { refund: AdminRefund & { settlement_impact_status: string; provider_accepted_at: string | null; updated_at: string }; subject_type: "BOOKING" | "VERIFICATION" | "SAFARI"; verification_id: number | null; safari_request_id: number | null; subject_reference: string | null; booking_id: number | null; booking_reference: string | null; booking_status: string | null; customer_id: number | null; customer_name: string | null; hotel_id: number | null; hotel_name: string | null; cancellation_id: number | null; cancellation_type: string | null; cancellation_status: string | null; cancellation_reason: string | null; approved_refund_amount: string; refunded_amount: string; payment_id: number; captured_amount: string; payment_status: string; }
export interface AdminIssue { category: string; booking_id: number; booking_reference: string; hotel_id: number; status: string; summary: string; created_at: string; }
export interface AdminDispute { id: number; hotel_id: number; customer_id: number; booking_id: number | null; subject: string; kind: string; status: string; message_count: number; updated_at: string; }
export interface AdminConversationMessage { id: number; sender: string; is_mine: boolean; body: string; created_at: string; }
export interface AdminConversation { id: number; hotel_id: number; hotel_name: string; booking_id: number | null; booking_reference: string | null; subject: string; kind: string; status: string; unread_count: number; last_message_at: string | null; created_at: string; updated_at: string; messages: AdminConversationMessage[]; }
export interface AdminNotification { id: number; recipient_user_id: number; event_type: string; title: string; read_at: string | null; created_at: string; delivery_statuses: Record<string, string>; }
export interface AuditLog { id: number; actor_user_id: number; action: string; target_type: string; target_id: string; previous_value: Record<string, unknown> | null; new_value: Record<string, unknown> | null; reason: string; created_at: string; }

export const controlService = {
  overview: () => authorizedApi.get<Overview>("/admin/control/overview"),
  users: (query = "") => authorizedApi.get<AdminUser[]>(`/admin/control/users${query}`),
  updateUser: (id: number, status: string, reason: string) => authorizedApi.patch<AdminUser, { status: string; reason: string }>(`/admin/control/users/${id}/status`, { status, reason }),
  updateHotel: (id: number, status: HotelStatus, reason: string) => authorizedApi.patch<Hotel, { status: HotelStatus; reason: string }>(`/admin/control/hotels/${id}/status`, { status, reason }),
  bookings: () => authorizedApi.get<AdminBooking[]>("/admin/control/bookings"),
  hotelCausedCancellation: (bookingId: number, reason: string) => authorizedApi.post<AdminCancellation, { reason: string }>(`/admin/bookings/${bookingId}/hotel-caused-cancellation`, { reason }),
  payments: () => authorizedApi.get<AdminPayment[]>("/admin/control/payments"),
  payment: (id: number) => authorizedApi.get<AdminPaymentDetail>(`/admin/control/payments/${id}`),
  reconcilePayment: (id: number, action: "RETRY_CONFIRMATION" | "REFUND_REQUIRED" | "MANUAL_REVIEW", reason: string) => authorizedApi.post<AdminPaymentDetail, { action: string; reason: string }>(`/admin/control/payments/${id}/reconciliation`, { action, reason }),
  cancellations: () => authorizedApi.get<AdminCancellation[]>("/admin/control/cancellations"),
  decideManualRefund: (cancellationId: number, approvedAmount: string, note: string) => authorizedApi.post<AdminCancellation, { approved_amount: string; note: string }>(`/admin/cancellations/${cancellationId}/manual-refund`, { approved_amount: approvedAmount, note }),
  refunds: () => authorizedApi.get<AdminRefund[]>("/admin/control/refunds"),
  refund: (id: number) => authorizedApi.get<AdminRefundDetail>(`/admin/control/refunds/${id}`),
  refundAction: (id: number, action: "RETRY" | "RECONCILE" | "MANUAL_REVIEW", reason: string) => authorizedApi.post<AdminRefundDetail, { action: string; reason: string }>(`/admin/control/refunds/${id}/action`, { action, reason }),
  noShows: () => authorizedApi.get<AdminIssue[]>("/admin/control/no-shows"),
  hotelFailures: () => authorizedApi.get<AdminIssue[]>("/admin/control/hotel-failures"),
  disputes: () => authorizedApi.get<AdminDispute[]>("/admin/control/disputes"),
  inspectConversation: (conversationId: number, reason: string) => authorizedApi.post<AdminConversation, { reason: string }>(`/admin/conversations/${conversationId}/inspect`, { reason }),
  notifications: () => authorizedApi.get<AdminNotification[]>("/admin/control/notifications"),
  audit: (query = "") => authorizedApi.get<AuditLog[]>(`/admin/control/audit${query}`),
};
