export type PropertyType = "HOTEL" | "RESORT" | "VILLA" | "APARTMENT" | "HOSTEL" | "HOMESTAY";
export type HotelStatus = "DRAFT" | "PENDING" | "ACTIVE" | "INACTIVE" | "SUSPENDED";
export type BookingGatewayStatus = "ACTIVE" | "BOOKING_ON_REQUEST" | "PAUSED";
export type VerificationStatus = "PENDING" | "APPROVED" | "REJECTED" | "ADDITIONAL_INFO_REQUIRED" | "NEEDS_CHANGES";
export type PaymentStatus = "NOT_STARTED" | "PENDING" | "PAID" | "FAILED" | "REFUND_PENDING" | "REFUNDED";
export type RefundStatus = "PENDING" | "PROCESSING" | "RETRY_REQUIRED" | "RECONCILIATION_REQUIRED" | "SUCCEEDED" | "FAILED" | "PARTIAL" | "MANUAL_REVIEW";
export type BusinessType = "PROPRIETORSHIP" | "PARTNERSHIP" | "PRIVATE_LIMITED" | "PUBLIC_LIMITED" | "LLP" | "OTHER";
export type OperationBookingStatus = "CONFIRMED" | "CHECK_IN_ISSUE" | "CHECKED_IN" | "CHECKED_OUT" | "NO_SHOW";
export type CheckInIssueType = "MISSING_OR_INVALID_ID" | "BOOKING_MISMATCH" | "OPERATIONAL_VERIFICATION";

export interface OperationBooking {
  id: number;
  booking_reference: string;
  operation_qr_token: string | null;
  status: OperationBookingStatus;
  check_in: string;
  check_out: string;
  rooms: number;
  assigned_room: string | null;
  checked_in_at: string | null;
  checked_out_at: string | null;
  room_snapshot: { name?: string; bed_type?: string; max_guests?: number };
  primary_guest_name: string | null;
  status_note: string | null;
  is_system_generated: boolean;
  no_show_reminder_sent_at: string | null;
  no_show_eligible_at: string | null;
  auto_checkout_eligible_at: string | null;
  can_check_in: boolean;
  can_check_out: boolean;
  can_report_no_show: boolean;
  requires_financial_review: boolean;
}

export interface OperationBoard {
  generated_at: string;
  arrivals: OperationBooking[];
  checked_in: OperationBooking[];
  upcoming_checkouts: OperationBooking[];
  no_show_actions: OperationBooking[];
  check_in_issues: OperationBooking[];
}

export type SettlementStatus = "ON_HOLD" | "ELIGIBLE" | "PROCESSING" | "SETTLED" | "RECONCILIATION_REQUIRED";
export type PayoutStatus = "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED" | "RECONCILIATION_REQUIRED" | "REVERSED";
export interface SettlementAdjustment { id: number; kind: "ADJUSTMENT" | "REVERSAL"; amount: string; reason: string; applies_to_current_settlement: boolean; applied_to_settlement_id: number | null; applied_at: string | null; created_at: string; }
export interface SettlementEvent { id: number; old_status: SettlementStatus | null; new_status: SettlementStatus; note: string; actor_user_id: number | null; created_at: string; }
export interface SettlementData {
  id: number; hotel_id: number; booking_id: number; currency: string; gross_amount: string; commission_rate: string | null; commission_rule: string | null; vayora_fee: string; refund_deductions: string; adjustment_total: string; net_payable: string;
  eligibility_date: string; status: SettlementStatus; hold_reason: string | null; processing_at: string | null; settled_at: string | null; created_at: string;
  booking: { id: number; booking_reference: string; check_in: string; check_out: string; checked_out_at: string | null; status: string; payment_status: string; policy_snapshot: Record<string, unknown>; payments: Array<{ id: number; amount: string; currency: string; status: string; reconciliation_status: string }>; cancellation: { id: number; cancellation_type: string; status: string; refundable_amount: string; refunded_amount: string; requires_manual_review: boolean; refunds: Array<{ id: number; amount: string; status: string }> } | null };
  hotel: { id: number; name: string }; adjustments: SettlementAdjustment[]; events: SettlementEvent[];
  payout: { provider_utr: string | null; status: PayoutStatus; amount: string; currency: string; failure_reason: string | null; reconciliation_reason: string | null; initiated_at: string | null; completed_at: string | null } | null;
}

export type ReviewChallengeReason = "FAKE_OR_MISLEADING" | "WRONG_PROPERTY" | "SPAM" | "ABUSIVE_CONTENT" | "PERSONAL_INFORMATION" | "EXTORTION" | "MANIPULATION" | "OTHER_POLICY_VIOLATION";
export interface PartnerReview {
  id: number; booking_id: number; hotel_id: number; overall_rating: number; cleanliness_rating: number; service_rating: number; location_rating: number; room_quality_rating: number; value_rating: number; review_text: string; verified_stay: boolean; moderation_status: "PUBLISHED" | "PENDING_REVIEW" | "REJECTED"; created_at: string;
  hotel: { id: number; name: string }; booking: { id: number; booking_reference: string; checked_out_at: string | null }; hotel_response: { id: number; response_text: string; created_at: string } | null; challenge: { id: number; reason: ReviewChallengeReason; details: string; status: "OPEN" | "UPHELD" | "DISMISSED"; resolution_note: string | null; created_at: string; resolved_at: string | null } | null;
}

export interface HotelData {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  property_type: PropertyType;
  star_rating: number;
  status: HotelStatus;
  booking_gateway_status: BookingGatewayStatus;
  profile_completion_percent: number;
  is_profile_complete: boolean;
  address_line1: string;
  address_line2: string | null;
  city: string;
  district: string | null;
  state: string;
  country: string;
  postal_code: string;
  latitude: number | null;
  longitude: number | null;
  contact_email: string | null;
  contact_phone: string | null;
  check_in_time: string;
  check_out_time: string;
  is_featured: boolean;
  partner_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AmenityData { id: number; name: string; slug: string; icon: string | null; category: string | null; is_active: boolean; }
export interface HotelImageData { id: number; hotel_id: number; image_url: string; storage_key: string | null; content_type: string | null; file_size: number | null; alt_text: string | null; is_cover: boolean; display_order: number; created_at: string; }
export interface PartnerHotelProfile extends HotelData { images: HotelImageData[]; amenities: AmenityData[]; verification_status: VerificationStatus | null; }
export type PartnerProfileUpdate = Partial<Pick<CreateHotelInput, "name" | "description" | "property_type" | "address_line1" | "address_line2" | "city" | "district" | "state" | "postal_code" | "contact_email" | "contact_phone" | "check_in_time" | "check_out_time">>;

export interface VerificationData {
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
  fee: VerificationFeeStatus | null;
}

export interface VerificationFeeStatus {
  amount: string;
  currency: string;
  payment_status: PaymentStatus;
  payment_id: number | null;
  provider_order_id: string | null;
  payment_reference: string | null;
  paid_at: string | null;
  refund_status: RefundStatus | null;
  refund_id: number | null;
  refund_reference: string | null;
  refund_failure_reason: string | null;
  disclaimer: string;
}

export interface VerificationPaymentOrder extends PaymentOrder {
  purpose: "VERIFICATION_FEE";
}

export interface PartnerOverview {
  hotel: HotelData | null;
  verification: VerificationData | null;
  has_hotel: boolean;
  is_onboarding_complete: boolean;
  can_access_portal: boolean;
  verification_fee: VerificationFeeStatus | null;
}

export interface CreateHotelInput {
  name: string;
  slug: string;
  description?: string;
  property_type: PropertyType;
  star_rating?: number;
  address_line1: string;
  address_line2?: string;
  city: string;
  district?: string;
  state?: string;
  country?: string;
  postal_code: string;
  latitude?: number;
  longitude?: number;
  contact_email?: string;
  contact_phone?: string;
  check_in_time: string;
  check_out_time: string;
}

export interface SubmitVerificationInput {
  business_name: string;
  business_type: BusinessType;
  gstin?: string;
  pan?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  bank_name?: string;
  bank_beneficiary_name?: string;
  document_proof_type?: string;
  document_reference?: string;
}

export type RoomTypeStatus = "DRAFT" | "PENDING" | "APPROVED" | "NEEDS_CHANGES" | "BOOKABLE";

export interface MealAddOnOption {
  name: string;
  price: number;
  currency: string;
}

export interface RoomImageData {
  id: number;
  room_type_id: number;
  image_url: string;
  alt_text?: string | null;
  is_cover: boolean;
  display_order: number;
  created_at: string;
}

export interface PartnerRoomType {
  id: number;
  hotel_id: number;
  name: string;
  description: string | null;
  max_adults: number;
  max_children: number;
  max_guests: number;
  bed_type: string;
  bed_count: number;
  room_size_sqm: number | null;
  base_price: number;
  currency: string;
  total_rooms: number;
  is_active: boolean;
  status: RoomTypeStatus;
  extra_bed_rules: string | null;
  meal_add_on_options: MealAddOnOption[];
  review_notes: string | null;
  reviewed_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  images: RoomImageData[];
  amenities: AmenityData[];
}

export interface PartnerRoomTypeInput {
  name: string;
  description?: string | null;
  max_adults: number;
  max_children: number;
  max_guests: number;
  bed_type: string;
  bed_count: number;
  room_size_sqm?: number | null;
  base_price: number;
  currency?: string;
  total_rooms: number;
  extra_bed_rules?: string | null;
  meal_add_on_options?: MealAddOnOption[];
  amenity_ids?: number[];
}

export interface RoomInventoryData {
  id: number;
  room_type_id: number;
  inventory_date: string;
  total_inventory: number;
  available_inventory: number;
  blocked_inventory: number;
  confirmed_inventory: number;
  held_inventory: number;
  price: number;
  is_closed: boolean;
  updated_at: string;
}

export interface InventoryRangeResponse {
  items: RoomInventoryData[];
  last_inventory_update: string | null;
}

export interface InventoryRangeUpdate {
  start_date: string;
  end_date: string;
  total_inventory?: number;
  blocked_inventory?: number;
  price?: number;
  is_closed?: boolean;
}

export interface BookingGatewayState {
  hotel_id: number;
  partner_requested_status: BookingGatewayStatus;
  effective_status: BookingGatewayStatus;
  override_status: BookingGatewayStatus | null;
  override_reason: string | null;
  overridden_at: string | null;
  inventory_last_updated_at: string | null;
  inventory_is_fresh: boolean;
  inventory_freshness_reason: string | null;
  verified: boolean;
}
import type { PaymentOrder } from "@/src/services/booking.service";
