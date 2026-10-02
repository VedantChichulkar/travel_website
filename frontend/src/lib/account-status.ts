import type { BookingStatus, PaymentStatus, Refund } from "@/src/services/booking.service";

export type StatusTone = "blue" | "green" | "amber" | "red" | "slate";
export interface StatusDisplay { label: string; detail: string; tone: StatusTone }

export const BOOKING_STATUS: Record<BookingStatus, StatusDisplay> = {
  PENDING: { label: "Request submitted", detail: "Waiting for the hotel to review this booking request.", tone: "blue" },
  REQUEST_REJECTED: { label: "Request declined", detail: "The hotel could not accept this request.", tone: "red" },
  REQUEST_EXPIRED: { label: "Request expired", detail: "The hotel response window ended before acceptance.", tone: "slate" },
  PAYMENT_PENDING: { label: "Payment required", detail: "The booking is accepted and waiting for payment.", tone: "amber" },
  CONFIRMED: { label: "Confirmed", detail: "Your hotel booking is confirmed.", tone: "green" },
  FAILED: { label: "Booking failed", detail: "The booking could not be completed.", tone: "red" },
  CANCELLATION_REQUESTED: { label: "Cancellation requested", detail: "The cancellation request is being processed.", tone: "amber" },
  CANCELLED: { label: "Cancelled", detail: "This booking is cancelled.", tone: "slate" },
  REFUND_PENDING: { label: "Refund in progress", detail: "A related refund is pending or under review.", tone: "amber" },
  REFUNDED: { label: "Refunded", detail: "The booking refund is complete.", tone: "green" },
  CHECK_IN_ISSUE: { label: "Check-in needs attention", detail: "Contact the property or Maharashtra Tourist Places for assistance.", tone: "red" },
  CHECKED_IN: { label: "Checked in", detail: "Your stay is currently in progress.", tone: "green" },
  CHECKED_OUT: { label: "Stay completed", detail: "Checkout is complete.", tone: "slate" },
  NO_SHOW: { label: "No-show recorded", detail: "The property recorded that check-in did not occur.", tone: "red" },
};

export const PAYMENT_STATUS: Record<PaymentStatus, StatusDisplay> = {
  NOT_STARTED: { label: "Not started", detail: "No payment session has been created.", tone: "slate" },
  PENDING: { label: "Payment pending", detail: "Waiting for verified provider confirmation.", tone: "amber" },
  PAID: { label: "Paid", detail: "Payment was verified by the backend.", tone: "green" },
  FAILED: { label: "Payment failed", detail: "The payment was not completed.", tone: "red" },
  REFUND_PENDING: { label: "Refund pending", detail: "The refund is being processed or reconciled.", tone: "amber" },
  REFUNDED: { label: "Refunded", detail: "The verified refund is complete.", tone: "green" },
};

export const REFUND_STATUS: Record<Refund["status"], StatusDisplay> = {
  PENDING: { label: "Refund pending", detail: "The refund instruction is queued.", tone: "amber" },
  PROCESSING: { label: "Refund processing", detail: "The provider is processing the refund.", tone: "blue" },
  RETRY_REQUIRED: { label: "Refund retrying", detail: "Maharashtra Tourist Places will retry the provider operation.", tone: "amber" },
  RECONCILIATION_REQUIRED: { label: "Refund needs review", detail: "Provider evidence needs reconciliation.", tone: "amber" },
  SUCCEEDED: { label: "Refund completed", detail: "The refund is complete.", tone: "green" },
  FAILED: { label: "Refund delayed", detail: "The provider operation failed and requires follow-up.", tone: "red" },
  PARTIAL: { label: "Partially refunded", detail: "A partial refund was completed.", tone: "amber" },
  MANUAL_REVIEW: { label: "Refund needs review", detail: "Maharashtra Tourist Places operations is reviewing the refund.", tone: "amber" },
};

export function statusClasses(tone: StatusTone): string {
  if (tone === "green") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (tone === "amber") return "border-amber-200 bg-amber-50 text-amber-800";
  if (tone === "red") return "border-red-200 bg-red-50 text-red-800";
  if (tone === "blue") return "border-blue-200 bg-blue-50 text-blue-800";
  return "border-slate-200 bg-slate-100 text-slate-700";
}

export function money(value: string, currency: string): string {
  const amount = Number(value);
  return Number.isFinite(amount) ? new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount) : `${currency} ${value}`;
}

export function date(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}
