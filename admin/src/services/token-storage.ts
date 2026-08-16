interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

const STORAGE_KEY = "travel-booking-admin-auth";

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/**
 * MVP trade-off: FastAPI returns both JWTs in JSON, so they are stored here in
 * localStorage to preserve the session across refreshes. This single adapter keeps
 * browser storage out of components and can be replaced with secure httpOnly
 * cookies once the backend supports them. localStorage is not production-grade
 * token storage because injected JavaScript can read it.
 */
export const tokenStorage = {
  get(): StoredTokens | null {
    const raw = storage()?.getItem(STORAGE_KEY);
    if (!raw) return null;

    try {
      const value: unknown = JSON.parse(raw);
      if (
        typeof value === "object" &&
        value !== null &&
        "accessToken" in value &&
        "refreshToken" in value &&
        typeof value.accessToken === "string" &&
        typeof value.refreshToken === "string"
      ) {
        return { accessToken: value.accessToken, refreshToken: value.refreshToken };
      }
    } catch {
      // Corrupt or modified storage is treated as an unauthenticated session.
    }

    this.clear();
    return null;
  },

  set(tokens: StoredTokens): void {
    storage()?.setItem(STORAGE_KEY, JSON.stringify(tokens));
  },

  updateAccessToken(accessToken: string): void {
    const current = this.get();
    if (current) this.set({ ...current, accessToken });
  },

  clear(): void {
    storage()?.removeItem(STORAGE_KEY);
  },
};
