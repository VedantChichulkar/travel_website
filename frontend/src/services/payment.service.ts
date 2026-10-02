import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type { PaymentOrder } from "@/src/services/booking.service";

function token(): string {
  const value = tokenStorage.getTokens()?.accessToken;
  if (!value) throw new Error("Sign in before confirming payment.");
  return value;
}

export const paymentService = {
  confirm(paymentId: number, body: { provider_order_id: string; provider_payment_id: string; signature: string }) {
    return api.post<PaymentOrder, typeof body>(`/bookings/payments/${paymentId}/confirm`, body, token());
  },
};
