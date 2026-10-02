import { api } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type { ContactConfig, SupportEnquiryInput, SupportEnquiryReceipt } from "@/src/types/support";

export const supportService = {
  config: () => api.get<ContactConfig>("/support/config"),
  submit: (data: SupportEnquiryInput) => api.post<SupportEnquiryReceipt, SupportEnquiryInput>("/support/enquiries", data, tokenStorage.getTokens()?.accessToken),
};
