import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";

export interface InventoryHold {
  hold_token: string;
  expires_at: string;
  status: "ACTIVE" | "EXPIRED" | "CONVERTED" | "CANCELLED";
}

export interface BookingQuote {
  hotel_id: number;
  room_type_id: number;
  check_in: string;
  check_out: string;
  rooms: number;
  adults: number;
  children: number;
  nights: number;
  currency: string;
  nightly_prices: { date: string; unit_price: string; rooms: number; amount: string }[];
  subtotal: string;
  taxes: string;
  platform_fee: string;
  discount: string;
  total_amount: string;
  booking_mode: "ACTIVE" | "BOOKING_ON_REQUEST" | "PAUSED";
}

export interface TravellerInput { full_name: string; age: number; is_primary: boolean; }

export type BookingStatus = "PENDING" | "REQUEST_REJECTED" | "REQUEST_EXPIRED" | "PAYMENT_PENDING" | "CONFIRMED" | "FAILED" | "CANCELLATION_REQUESTED" | "CANCELLED" | "REFUND_PENDING" | "REFUNDED" | "CHECK_IN_ISSUE" | "CHECKED_IN" | "CHECKED_OUT" | "NO_SHOW";
export type PaymentStatus = "NOT_STARTED" | "PENDING" | "PAID" | "FAILED" | "REFUND_PENDING" | "REFUNDED";

export interface PaymentOrder {
  id: number;
  booking_id: number;
  purpose: "BOOKING" | "VERIFICATION_FEE" | "ADVERTISING_CAMPAIGN" | "SAFARI_BOOKING";
  provider: string;
  provider_order_id: string;
  provider_payment_id: string | null;
  amount: string;
  currency: string;
  status: PaymentStatus;
  reconciliation_status: "NOT_REQUIRED" | "CONFIRMATION_REQUIRED" | "REFUND_REQUIRED" | "MANUAL_REVIEW" | "RESOLVED";
  failure_reason: string | null;
  verified_at: string | null;
  receipt_status: string;
  reconciliation_attempts: number;
  reconciliation_next_retry_at: string | null;
  reconciliation_reason: string | null;
  created_at: string;
  checkout_key_id: string | null;
}
export interface CustomerPayment extends PaymentOrder { booking_reference: string; hotel_name: string; }
export interface PaymentReceipt { booking_reference: string; payment_reference: string; provider_order_id: string; paid_at: string; hotel_name: string; amount: string; currency: string; payment_status: PaymentStatus; reconciliation_status: PaymentOrder["reconciliation_status"]; }

export interface Refund {
  id: number; amount: string; currency: string; status: "PENDING" | "PROCESSING" | "RETRY_REQUIRED" | "RECONCILIATION_REQUIRED" | "SUCCEEDED" | "FAILED" | "PARTIAL" | "MANUAL_REVIEW"; provider: string; provider_refund_id: string | null; provider_status: string | null; failure_reason: string | null; reconciliation_reason: string | null; provider_accepted_at: string | null; completed_at: string | null; created_at: string; settlement_impact_status: string;
}
export interface Cancellation {
  id: number; status: "REQUESTED" | "REFUND_PENDING" | "MANUAL_REVIEW" | "COMPLETED" | "REJECTED"; cancellation_type: "CUSTOMER" | "HOTEL_CAUSED" | "NO_SHOW" | "PAYMENT_RECONCILIATION"; refundable_amount: string; refunded_amount: string; requires_manual_review: boolean; refunds: Refund[];
}
export interface CustomerBooking { id: number; booking_reference: string; hotel: { id: number; name: string; slug: string; city: string; state: string; country: string }; room: { id: number; name: string; bed_type: string; currency: string }; check_in: string; check_out: string; rooms: number; adults: number; children: number; nights: number; status: BookingStatus; payment_status: PaymentStatus; subtotal: string; taxes: string; platform_fee: string; discount: string; total_amount: string; currency: string; room_snapshot: Record<string, unknown>; price_snapshot: Record<string, unknown>; policy_snapshot: Record<string, unknown>; booking_mode: "ACTIVE" | "BOOKING_ON_REQUEST" | "PAUSED"; request_expires_at: string | null; request_decided_at: string | null; request_decision_reason: string | null; payment_expires_at: string | null; created_at: string; updated_at: string; travellers?: Array<{ id: number; full_name: string; age: number; is_primary: boolean }>; }
export type ReviewModerationStatus = "PUBLISHED" | "PENDING_REVIEW" | "REJECTED";
export interface ReviewInput { overall_rating: number; cleanliness_rating: number; service_rating: number; location_rating: number; room_quality_rating: number; value_rating: number; review_text: string; }
export interface ReviewData extends ReviewInput { id: number; booking_id: number; hotel_id: number; verified_stay: boolean; moderation_status: ReviewModerationStatus; created_at: string; hotel: { id: number; name: string }; booking: { id: number; booking_reference: string; checked_out_at: string | null }; hotel_response: { id: number; response_text: string; created_at: string } | null; challenge: { id: number; reason: string; details: string; status: string; resolution_note: string | null; created_at: string; resolved_at: string | null } | null; }

function token() {
  const value = tokenStorage.getTokens()?.accessToken;
  if (!value) throw new Error("Please sign in to reserve this room.");
  return value;
}

export const bookingService = {
  quote(data: { hotel_id: number; room_type_id: number; check_in: string; check_out: string; rooms: number; adults: number; children: number }) {
    return api.post<BookingQuote, typeof data>("/bookings/quote", data, token());
  },
  createHold(data: { hotel_id: number; room_type_id: number; check_in: string; check_out: string; rooms: number; adults: number; children: number }) {
    return api.post<InventoryHold, typeof data>("/bookings/holds", data, token());
  },
  createBooking(data: { hotel_id: number; room_type_id: number; check_in: string; check_out: string; rooms: number; adults: number; children: number; hold_token: string; idempotency_key: string; travellers: TravellerInput[] }) {
    return api.post<CustomerBooking, typeof data>("/bookings", data, token());
  },
  createPaymentOrder(bookingId: number) {
    return api.post<PaymentOrder, Record<string, never>>(`/bookings/${bookingId}/payments/orders`, {}, token());
  },
  listMine() { return api.get<{ items: CustomerBooking[] }>("/bookings/me", token()); },
  getBooking(bookingId: number) { return api.get<CustomerBooking>(`/bookings/${bookingId}`, token()); },
  getPaymentHistory(bookingId: number) { return api.get<{ items: PaymentOrder[]; total: number }>(`/bookings/${bookingId}/payments`, token()); },
  listPaymentHistory() { return api.get<{ items: CustomerPayment[]; total: number }>("/bookings/payments/me", token()); },
  getReceipt(bookingId: number, paymentId: number) { return api.get<PaymentReceipt>(`/bookings/${bookingId}/payments/${paymentId}/receipt`, token()); },
  getReview(bookingId: number) { return api.get<ReviewData>(`/bookings/${bookingId}/review`, token()); },
  createReview(bookingId: number, data: ReviewInput) { return api.post<ReviewData, ReviewInput>(`/bookings/${bookingId}/review`, data, token()); },
  getCancellation(bookingId: number) { return api.get<Cancellation | null>(`/bookings/${bookingId}/cancellation`, token()); },
  requestCancellation(bookingId: number, reason: string) { return api.post<Cancellation, { reason: string }>(`/bookings/${bookingId}/cancellations`, { reason }, token()); },
};
