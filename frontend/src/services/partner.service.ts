import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type {
  CreateHotelInput,
  AmenityData,
  HotelData,
  HotelImageData,
  PartnerHotelProfile,
  PartnerProfileUpdate,
  PartnerOverview,
  SubmitVerificationInput,
  VerificationData,
  PartnerRoomType,
  PartnerRoomTypeInput,
  RoomImageData,
  InventoryRangeResponse,
  InventoryRangeUpdate,
  BookingGatewayState,
  BookingGatewayStatus,
  CheckInIssueType,
  OperationBoard,
  OperationBooking,
  SettlementData,
  PartnerReview,
  ReviewChallengeReason,
  VerificationFeeStatus,
  VerificationPaymentOrder,
} from "@/src/types/partner";
import type { CustomerBooking } from "@/src/services/booking.service";

function getAccessToken(): string {
  const tokens = tokenStorage.getTokens();
  if (!tokens?.accessToken) throw new Error("Not authenticated");
  return tokens.accessToken;
}

export const partnerService = {
  async getBookingRequests(): Promise<{ items: CustomerBooking[]; total: number }> {
    return api.get<{ items: CustomerBooking[]; total: number }>("/partner/booking-requests", getAccessToken());
  },
  async getBookings(): Promise<{ items: CustomerBooking[]; total: number }> {
    return api.get<{ items: CustomerBooking[]; total: number }>("/partner/bookings", getAccessToken());
  },
  async acceptBookingRequest(bookingId: number): Promise<CustomerBooking> {
    return api.post<CustomerBooking, Record<string, never>>(`/partner/booking-requests/${bookingId}/accept`, {}, getAccessToken());
  },
  async rejectBookingRequest(bookingId: number, reason: string): Promise<CustomerBooking> {
    return api.post<CustomerBooking, { reason: string }>(`/partner/booking-requests/${bookingId}/reject`, { reason }, getAccessToken());
  },
  async getReviews(): Promise<PartnerReview[]> { return api.get<PartnerReview[]>("/partner/reviews", getAccessToken()); },
  async respondToReview(reviewId: number, response_text: string): Promise<PartnerReview> { return api.post<PartnerReview, { response_text: string }>(`/partner/reviews/${reviewId}/response`, { response_text }, getAccessToken()); },
  async challengeReview(reviewId: number, reason: ReviewChallengeReason, details: string): Promise<PartnerReview> { return api.post<PartnerReview, { reason: ReviewChallengeReason; details: string }>(`/partner/reviews/${reviewId}/challenge`, { reason, details }, getAccessToken()); },
  async getSettlements(): Promise<SettlementData[]> { return api.get<SettlementData[]>("/partner/settlements", getAccessToken()); },
  async getSettlement(settlementId: number): Promise<SettlementData> { return api.get<SettlementData>(`/partner/settlements/${settlementId}`, getAccessToken()); },
  async getOperationsBoard(): Promise<OperationBoard> {
    return api.get<OperationBoard>("/partner/operations", getAccessToken());
  },
  async lookupOperation(data: { booking_id?: number; booking_reference?: string; qr_token?: string }): Promise<OperationBooking> {
    return api.post<OperationBooking, typeof data>("/partner/operations/lookup", data, getAccessToken());
  },
  async checkInOperation(bookingId: number, assigned_room: string): Promise<OperationBooking> { return api.post<OperationBooking, { assigned_room: string }>(`/partner/operations/bookings/${bookingId}/check-in`, { assigned_room }, getAccessToken()); },
  async checkOutOperation(bookingId: number): Promise<OperationBooking> { return api.post<OperationBooking, Record<string, never>>(`/partner/operations/bookings/${bookingId}/check-out`, {}, getAccessToken()); },
  async issueOperation(bookingId: number, issue_type: CheckInIssueType, reason: string): Promise<OperationBooking> { return api.post<OperationBooking, { issue_type: CheckInIssueType; reason: string }>(`/partner/operations/bookings/${bookingId}/check-in-issue`, { issue_type, reason }, getAccessToken()); },
  async noShowOperation(bookingId: number): Promise<OperationBooking> { return api.post<OperationBooking, Record<string, never>>(`/partner/operations/bookings/${bookingId}/no-show`, {}, getAccessToken()); },
  async runOperationFallbacks(): Promise<OperationBooking[]> { return api.post<OperationBooking[], Record<string, never>>("/partner/operations/run-fallbacks", {}, getAccessToken()); },
  async getOverview(): Promise<PartnerOverview> {
    const token = getAccessToken();
    return api.get<PartnerOverview>("/partner/hotel", token);
  },

  async getVerificationFee(): Promise<VerificationFeeStatus> {
    return api.get<VerificationFeeStatus>("/partner/verification/fee", getAccessToken());
  },

  async createVerificationFeePaymentOrder(): Promise<VerificationPaymentOrder> {
    return api.post<VerificationPaymentOrder, Record<string, never>>("/partner/verification/fee/payment-order", {}, getAccessToken());
  },

  async createHotel(data: CreateHotelInput): Promise<HotelData> {
    const token = getAccessToken();
    return api.post<HotelData, CreateHotelInput>("/partner/hotel", data, token);
  },

  async updateHotel(data: Partial<CreateHotelInput>): Promise<HotelData> {
    const token = getAccessToken();
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/partner/hotel`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const msg =
        typeof err.detail === "string"
          ? err.detail
          : response.status >= 500
          ? "Server error. Please try again."
          : "Update failed.";
      throw new Error(msg);
    }
    return response.json() as Promise<HotelData>;
  },

  async getProfile(): Promise<PartnerHotelProfile> {
    return api.get<PartnerHotelProfile>("/partner/profile", getAccessToken());
  },

  async updateProfile(data: PartnerProfileUpdate): Promise<PartnerHotelProfile> {
    return api.patch<PartnerHotelProfile, PartnerProfileUpdate>("/partner/profile", data, getAccessToken());
  },

  async getFacilities(): Promise<AmenityData[]> {
    return api.get<AmenityData[]>("/partner/profile/facilities", getAccessToken());
  },

  async updateFacilities(amenity_ids: number[]): Promise<PartnerHotelProfile> {
    return api.put<PartnerHotelProfile, { amenity_ids: number[] }>("/partner/profile/facilities", { amenity_ids }, getAccessToken());
  },

  async addProfileImage(data: { image_url: string; alt_text?: string; is_cover?: boolean; display_order?: number }): Promise<HotelImageData> {
    return api.post<HotelImageData, typeof data>("/partner/profile/images", data, getAccessToken());
  },

  async deleteProfileImage(imageId: number): Promise<void> {
    await api.delete<void>(`/partner/profile/images/${imageId}`, getAccessToken());
  },

  async uploadProfileImage(file: File, altText?: string): Promise<HotelImageData> {
    const form = new FormData();
    form.append("file", file);
    if (altText) form.append("alt_text", altText);
    return api.post<HotelImageData, FormData>("/partner/profile/images/upload", form, getAccessToken());
  },

  async setProfilePrimaryImage(imageId: number): Promise<HotelImageData> {
    return api.patch<HotelImageData, Record<string, never>>(`/partner/profile/images/${imageId}/primary`, {}, getAccessToken());
  },

  async reorderProfileImages(imageIds: number[]): Promise<HotelImageData[]> {
    return api.put<HotelImageData[], { image_ids: number[] }>("/partner/profile/images/order", { image_ids: imageIds }, getAccessToken());
  },

  async submitVerification(data: SubmitVerificationInput): Promise<VerificationData> {
    const token = getAccessToken();
    return api.post<VerificationData, SubmitVerificationInput>("/partner/verification", data, token);
  },

  async uploadVerificationDocument(file: File): Promise<{ document_reference: string; original_name: string; content_type: string; size: number }> {
    const form = new FormData(); form.append("file", file);
    return api.post<{ document_reference: string; original_name: string; content_type: string; size: number }, FormData>("/partner/verification/document", form, getAccessToken());
  },

  async getVerification(): Promise<VerificationData> {
    const token = getAccessToken();
    return api.get<VerificationData>("/partner/verification", token);
  },

  // ─── Room Type Management ───────────────────────────────────────────────────

  async getRoomTypes(): Promise<PartnerRoomType[]> {
    return api.get<PartnerRoomType[]>("/partner/room-types", getAccessToken());
  },

  async getRoomType(roomId: number): Promise<PartnerRoomType> {
    return api.get<PartnerRoomType>(`/partner/room-types/${roomId}`, getAccessToken());
  },

  async createRoomType(data: PartnerRoomTypeInput): Promise<PartnerRoomType> {
    return api.post<PartnerRoomType, PartnerRoomTypeInput>("/partner/room-types", data, getAccessToken());
  },

  async updateRoomType(roomId: number, data: PartnerRoomTypeInput): Promise<PartnerRoomType> {
    return api.put<PartnerRoomType, PartnerRoomTypeInput>(`/partner/room-types/${roomId}`, data, getAccessToken());
  },

  async deleteRoomType(roomId: number): Promise<void> {
    await api.delete<void>(`/partner/room-types/${roomId}`, getAccessToken());
  },

  async submitRoomType(roomId: number): Promise<PartnerRoomType> {
    return api.post<PartnerRoomType, Record<string, never>>(`/partner/room-types/${roomId}/submit`, {}, getAccessToken());
  },

  async addRoomImage(roomId: number, data: { image_url: string; alt_text?: string; is_cover?: boolean; display_order?: number }): Promise<RoomImageData> {
    return api.post<RoomImageData, typeof data>(`/partner/room-types/${roomId}/images`, data, getAccessToken());
  },

  async uploadRoomImage(roomId: number, file: File, altText?: string, isCover?: boolean): Promise<RoomImageData> {
    const form = new FormData();
    form.append("file", file);
    if (altText) form.append("alt_text", altText);
    if (isCover !== undefined) form.append("is_cover", String(isCover));
    return api.post<RoomImageData, FormData>(`/partner/room-types/${roomId}/images/upload`, form, getAccessToken());
  },

  async setRoomCoverImage(roomId: number, imageId: number): Promise<RoomImageData> {
    return api.patch<RoomImageData, Record<string, never>>(`/partner/room-types/${roomId}/images/${imageId}/cover`, {}, getAccessToken());
  },

  async deleteRoomImage(roomId: number, imageId: number): Promise<void> {
    await api.delete<void>(`/partner/room-types/${roomId}/images/${imageId}`, getAccessToken());
  },

  async getRoomInventory(roomId: number, startDate: string, endDate: string): Promise<InventoryRangeResponse> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    return api.get<InventoryRangeResponse>(`/partner/room-types/${roomId}/inventory?${params}`, getAccessToken());
  },

  async updateRoomInventory(roomId: number, data: InventoryRangeUpdate): Promise<InventoryRangeResponse> {
    return api.put<InventoryRangeResponse, InventoryRangeUpdate>(`/partner/room-types/${roomId}/inventory`, data, getAccessToken());
  },

  async getBookingGateway(): Promise<BookingGatewayState> {
    return api.get<BookingGatewayState>("/partner/booking-gateway", getAccessToken());
  },

  async updateBookingGateway(booking_gateway_status: BookingGatewayStatus): Promise<BookingGatewayState> {
    return api.patch<BookingGatewayState, { booking_gateway_status: BookingGatewayStatus }>("/partner/booking-gateway", { booking_gateway_status }, getAccessToken());
  },
};
