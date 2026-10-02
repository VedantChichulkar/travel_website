import type { PaymentOrder } from "@/src/services/booking.service";
import { paymentService } from "@/src/services/payment.service";

type RazorpayResult = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };
type RazorpayOptions = {
  key: string; order_id: string; amount: number; currency: string; name: string; description: string;
  handler: (result: RazorpayResult) => void; modal: { ondismiss: () => void; confirm_close: boolean };
  retry: { enabled: boolean };
};
type RazorpayInstance = { open: () => void; on: (event: string, callback: (value: unknown) => void) => void };

declare global { interface Window { Razorpay?: new (options: RazorpayOptions) => RazorpayInstance } }

let checkoutScript: Promise<void> | null = null;

function loadRazorpay(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("Checkout is available only in a browser."));
  if (window.Razorpay) return Promise.resolve();
  if (checkoutScript) return checkoutScript;
  checkoutScript = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => { checkoutScript = null; reject(new Error("Secure checkout could not be loaded.")); };
    document.head.appendChild(script);
  });
  return checkoutScript;
}

export async function openPaymentCheckout(order: PaymentOrder, description: string): Promise<PaymentOrder> {
  if (order.provider !== "RAZORPAY" || !order.checkout_key_id) {
    throw new Error("This payment order uses the local signed sandbox and has no hosted checkout.");
  }
  await loadRazorpay();
  return new Promise((resolve, reject) => {
    const Razorpay = window.Razorpay;
    if (!Razorpay) return reject(new Error("Secure checkout is unavailable."));
    let settled = false;
    const checkout = new Razorpay({
      key: order.checkout_key_id!, order_id: order.provider_order_id,
      amount: Math.round(Number(order.amount) * 100), currency: order.currency,
      name: "Maharashtra Tourist Places", description,
      retry: { enabled: true },
      modal: { confirm_close: true, ondismiss: () => { if (!settled) reject(new Error("Checkout was closed. Your payment order remains available to retry.")); } },
      handler: (result) => {
        settled = true;
        void paymentService.confirm(order.id, { provider_order_id: result.razorpay_order_id, provider_payment_id: result.razorpay_payment_id, signature: result.razorpay_signature }).then(resolve, reject);
      },
    });
    checkout.on("payment.failed", () => { /* Checkout remains open for provider-supported retry. */ });
    checkout.open();
  });
}
