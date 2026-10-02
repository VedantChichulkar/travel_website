import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type { Safari, SafariRequest } from "@/src/types/safari";
import type { PaymentOrder } from "@/src/services/booking.service";
const token = () => { const value = tokenStorage.getTokens()?.accessToken; if (!value) throw new Error("Sign in to manage safari requests."); return value; };
export const safariService = {
  list: () => api.get<Safari[]>("/safaris"), get: (slug: string) => api.get<Safari>(`/safaris/${slug}`),
  request: (slug: string, body: { preferred_date: string; preferred_shift?: string; preferred_booking_category?: string; preferred_vehicle_option?: string; visitor_count: number; alternate_preference?: string }) => api.post<SafariRequest, typeof body>(`/safaris/${slug}/requests`, body, token()),
  mine: () => api.get<SafariRequest[]>("/account/safaris", token()),
  getRequest: (id: number) => api.get<SafariRequest>(`/account/safaris/${id}`, token()),
  alternative: (id: number, alternative_id: number) => api.post<SafariRequest, { alternative_id: number }>(`/account/safaris/${id}/alternative`, { alternative_id }, token()),
  travellers: (id: number, travellers: Array<{ details: Record<string, unknown> }>) => api.put<SafariRequest, { travellers: Array<{ details: Record<string, unknown> }> }>(`/account/safaris/${id}/travellers`, { travellers }, token()),
  submitTravellers: (id: number) => api.post<SafariRequest, Record<string, never>>(`/account/safaris/${id}/travellers/submit`, {}, token()),
  uploadTravellerDocument: (requestId: number, travellerId: number, documentType: string, file: File) => { const body = new FormData(); body.set("document_type", documentType); body.set("file", file); return api.post(`/account/safaris/${requestId}/travellers/${travellerId}/documents`, body, token()); },
  payment: (id: number) => api.post<PaymentOrder, Record<string, never>>(`/account/safaris/${id}/payment-order`, {}, token()),
  download: async (requestId: number, documentId: number, filename: string) => { const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/account/safaris/${requestId}/documents/${documentId}`, { headers: { Authorization: `Bearer ${token()}` } }); if (!response.ok) throw new Error("Document download failed."); const url = URL.createObjectURL(await response.blob()); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url); },
};
