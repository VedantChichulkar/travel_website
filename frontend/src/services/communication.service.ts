import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type { ConversationData, ConversationKind, ConversationList, NotificationData, NotificationList } from "@/src/types/communication";

function token(): string { const value = tokenStorage.getTokens()?.accessToken; if (!value) throw new Error("Not authenticated"); return value; }

export const communicationService = {
  listConversations: () => api.get<ConversationList>("/communications/conversations", token()),
  getConversation: (id: number) => api.get<ConversationData>(`/communications/conversations/${id}`, token()),
  createConversation: (data: { hotel_id?: number; booking_id?: number; subject: string; message: string; kind?: ConversationKind }) => api.post<ConversationData, typeof data>("/communications/conversations", data, token()),
  sendMessage: (id: number, body: string) => api.post<ConversationData, { body: string }>(`/communications/conversations/${id}/messages`, { body }, token()),
  markConversationRead: (id: number) => api.post<ConversationData, Record<string, never>>(`/communications/conversations/${id}/read`, {}, token()),
  listNotifications: () => api.get<NotificationList>("/communications/notifications", token()),
  markNotificationRead: (id: number) => api.post<NotificationData, Record<string, never>>(`/communications/notifications/${id}/read`, {}, token()),
  markAllNotificationsRead: () => api.post<{ updated: number }, Record<string, never>>("/communications/notifications/read-all", {}, token()),
};
