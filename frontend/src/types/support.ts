export const ENQUIRY_TYPES = ["BOOKING_HELP", "SAFARI_HELP", "CANCELLATION_REFUND", "HOTEL_PARTNER", "GENERAL"] as const;
export type EnquiryType = (typeof ENQUIRY_TYPES)[number];

export interface ContactConfig {
  email: string | null;
  whatsapp_url: string | null;
}

export interface SupportEnquiryInput {
  idempotency_key: string;
  enquiry_type: EnquiryType;
  name: string;
  email: string;
  mobile: string;
  message: string;
  customer_reference?: string;
  property_name?: string;
  location?: string;
}

export interface SupportEnquiryReceipt {
  reference: string;
  enquiry_type: EnquiryType;
  created_at: string;
  next_step: string;
}
