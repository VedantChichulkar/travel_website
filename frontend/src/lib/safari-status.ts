import type { SafariStatus } from "@/src/types/safari";

export type SafariStatusTone = "blue" | "green" | "amber" | "red" | "slate";

export interface SafariStatusDisplay { label: string; description: string; nextAction: string; tone: SafariStatusTone; terminal: boolean }

export const SAFARI_STATUS: Record<SafariStatus, SafariStatusDisplay> = {
  AVAILABILITY_REQUESTED: { label: "Availability Request Sent", description: "Maharashtra Tourist Places has received your request and will begin checking external availability.", nextAction: "View request", tone: "blue", terminal: false },
  CHECKING_AVAILABILITY: { label: "Checking Availability", description: "Our team is checking your requested option with the relevant safari operation.", nextAction: "Wait for a response", tone: "blue", terminal: false },
  AWAITING_TRAVELLER_DETAILS: { label: "Traveller Details Required", description: "Availability is confirmed for this request or selected alternative. Complete the configured traveller requirements.", nextAction: "Complete traveller details", tone: "amber", terminal: false },
  DETAILS_SUBMITTED: { label: "Details Submitted", description: "Your traveller requirements are complete. Maharashtra Tourist Places operations is preparing the authoritative price.", nextAction: "Wait for price confirmation", tone: "blue", terminal: false },
  PAYMENT_PENDING: { label: "Payment Required", description: "The authoritative price is ready. Review it before creating a payment session.", nextAction: "Review and pay", tone: "amber", terminal: false },
  BOOKING_IN_PROGRESS: { label: "Official Booking in Progress", description: "Payment was received. Maharashtra Tourist Places is completing the external safari reservation; this is not yet confirmation.", nextAction: "View status", tone: "blue", terminal: false },
  CONFIRMED: { label: "Safari Confirmed", description: "The external safari booking has been completed. Review your reporting details and secure documents.", nextAction: "View booking and permit", tone: "green", terminal: true },
  NOT_AVAILABLE: { label: "Not Available", description: "The requested option could not be secured. Select an offered alternative if one is available.", nextAction: "Review alternatives", tone: "red", terminal: true },
  EXPIRED: { label: "Expired", description: "This request is no longer active.", nextAction: "Create a new request if needed", tone: "slate", terminal: true },
  CANCELLED: { label: "Cancelled", description: "This safari request was cancelled.", nextAction: "No action needed", tone: "slate", terminal: true },
  BOOKING_FAILED: { label: "Booking Needs Attention", description: "The external booking failed after payment. Refund and reconciliation status is shown below.", nextAction: "View refund status", tone: "red", terminal: true },
};

export function safariStatusDisplay(status: SafariStatus): SafariStatusDisplay { return SAFARI_STATUS[status]; }

export function safariStatusClasses(tone: SafariStatusTone): string {
  if (tone === "green") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800";
  if (tone === "red") return "border-red-200 bg-red-50 text-red-800";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800";
  return "border-slate-200 bg-slate-100 text-slate-700";
}
