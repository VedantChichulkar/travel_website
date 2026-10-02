export type SafariStatus = "AVAILABILITY_REQUESTED" | "CHECKING_AVAILABILITY" | "AWAITING_TRAVELLER_DETAILS" | "DETAILS_SUBMITTED" | "PAYMENT_PENDING" | "BOOKING_IN_PROGRESS" | "CONFIRMED" | "NOT_AVAILABLE" | "EXPIRED" | "CANCELLED" | "BOOKING_FAILED";
export interface Safari {
  id: number;
  name: string;
  slug: string;
  short_description: string;
  district_id?: number;
  destination_id?: number;
  district_name?: string;
  district_slug?: string;
  destination_name?: string;
  destination_slug?: string;
  destination_path?: string;
  hotel_destination_filter?: string;
  booking_categories: Array<{ code?: string; label?: string; [key: string]: unknown }>;
  vehicle_options: Array<{ code?: string; label?: string; [key: string]: unknown }>;
  shifts: string[];
  zones: string[];
  gates: string[];
  traveller_requirements: {
    fields?: Array<{ key: string; label?: string; required?: boolean; type?: string }>;
    documents?: Array<{ type: string; label?: string; required?: boolean }>;
  };
  official_reference_required: boolean;
  official_contact_required: boolean;
  official_document_required: boolean;
  source_url?: string;
  last_verified_at?: string;
  operational_notices: Array<{ id: number; title: string; body: string; severity: string; effective_from?: string; effective_until?: string; source_url?: string; last_verified_at?: string }>;
}
export interface SafariAlternative { id: number; safari_date: string; shift?: string; zone?: string; gate?: string; booking_category?: string; vehicle_option?: string; note?: string }
export interface SafariDocument { id: number; kind: string; document_type: string; original_name: string; content_type: string; size: number; created_at?: string }
export interface SafariTraveller { id: number; position: number; details: Record<string, unknown>; documents: SafariDocument[] }
export interface SafariRequest { id: number; request_reference: string; safari: Safari; preferred_date: string; preferred_shift?: string; preferred_booking_category?: string; preferred_vehicle_option?: string; visitor_count: number; alternate_preference?: string; status: SafariStatus; availability_result?: string; alternatives: SafariAlternative[]; selected_alternative_id?: number; target_response_at: string; responded_at?: string; overdue: boolean; payable_amount?: string; currency?: string; price_breakdown?: Record<string, unknown>; payment_status: string; payment_reconciliation_status?: string; refund_status?: string; travellers: SafariTraveller[]; confirmation_documents: SafariDocument[]; external_booking_reference?: string; confirmed_date?: string; confirmed_shift?: string; confirmed_zone?: string; confirmed_gate?: string; confirmed_booking_category?: string; confirmed_vehicle_option?: string; official_booking_contact_masked?: string; operator_confirmed_at?: string; reporting_instructions?: string; final_amount?: string; failure_reason?: string; created_at: string; updated_at: string }
