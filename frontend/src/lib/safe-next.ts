const FALLBACK_CUSTOMER_PATH = "/account";

export function safeCustomerNextPath(value: string | null | undefined) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return FALLBACK_CUSTOMER_PATH;

  try {
    const parsed = new URL(value, "https://travel-platform.local");
    if (parsed.origin !== "https://travel-platform.local") return FALLBACK_CUSTOMER_PATH;
    const allowed = parsed.pathname === "/account" || parsed.pathname.startsWith("/account/") || parsed.pathname === "/advertiser" || parsed.pathname.startsWith("/advertiser/") || parsed.pathname.startsWith("/safaris/");
    if (!allowed) return FALLBACK_CUSTOMER_PATH;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return FALLBACK_CUSTOMER_PATH;
  }
}

export function authPathWithNext(path: "/login" | "/register", next: string) {
  return `${path}?next=${encodeURIComponent(safeCustomerNextPath(next))}`;
}
