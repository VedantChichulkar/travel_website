import { ApiError, type PortalErrorDetail } from "@/src/services/api";
import type { User, UserRole } from "@/src/types/auth";
import type { PartnerOverview } from "@/src/types/partner";

export function isCustomerRole(role: UserRole): boolean {
  return role === "CUSTOMER" || role === "USER";
}

export function portalForRole(role: UserRole): { href: string; label: string } {
  if (role === "HOTEL_PARTNER") return { href: "/partner/login", label: "Hotel Partner login" };
  if (role === "ADMIN") {
    const adminPortalUrl = process.env.NEXT_PUBLIC_ADMIN_PORTAL_URL ?? (
      process.env.NODE_ENV === "development" ? "http://localhost:3001/login" : undefined
    );
    if (!adminPortalUrl) throw new Error("NEXT_PUBLIC_ADMIN_PORTAL_URL is not configured");
    return {
      href: adminPortalUrl,
      label: "Admin login",
    };
  }
  return { href: "/login", label: "Customer login" };
}

export function portalError(error: unknown): PortalErrorDetail | null {
  if (!(error instanceof ApiError)) return null;
  const detail = error.payload?.detail;
  if (
    detail &&
    !Array.isArray(detail) &&
    typeof detail !== "string" &&
    detail.code === "WRONG_PORTAL"
  ) {
    return detail;
  }
  return null;
}

export function signedInPortalMessage(user: User): string {
  const destination = portalForRole(user.role).label.replace(/ login$/, "");
  return `You are already signed in to the ${destination}. Use the matching portal to continue.`;
}

export function partnerEntryRoute(overview: PartnerOverview): string {
  if (!overview.has_hotel || !overview.verification) return "/partner/onboarding";
  if (overview.can_access_portal && overview.verification.verification_status === "APPROVED") {
    return "/partner/dashboard";
  }
  if (
    overview.verification.verification_status === "REJECTED" ||
    overview.verification.verification_status === "ADDITIONAL_INFO_REQUIRED"
  ) {
    return "/partner/onboarding";
  }
  return "/partner/verification";
}
