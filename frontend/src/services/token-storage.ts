interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

const STORAGE_KEY = "travel-booking-auth";

function getStorage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/**
 * MVP trade-off: the backend returns JWTs in JSON and cannot set httpOnly cookies.
 * Keeping all browser storage access here makes a future cookie-based migration
 * localized. localStorage remains readable by injected JavaScript, so the app must
 * maintain strong XSS hygiene and move to secure httpOnly cookies before production.
 */
export const tokenStorage = {
  getTokens(): StoredTokens | null {
    const value = getStorage()?.getItem(STORAGE_KEY);
    if (!value) return null;

    try {
      const parsed: unknown = JSON.parse(value);
      if (
        typeof parsed === "object" &&
        parsed !== null &&
        "accessToken" in parsed &&
        "refreshToken" in parsed &&
        typeof parsed.accessToken === "string" &&
        typeof parsed.refreshToken === "string"
      ) {
        return {
          accessToken: parsed.accessToken,
          refreshToken: parsed.refreshToken,
        };
      }
    } catch {
      // Invalid or manually modified storage is treated as a signed-out session.
    }

    this.clear();
    return null;
  },

  setTokens(tokens: StoredTokens): void {
    getStorage()?.setItem(STORAGE_KEY, JSON.stringify(tokens));
  },

  setAccessToken(accessToken: string): void {
    const current = this.getTokens();
    if (current) this.setTokens({ ...current, accessToken });
  },

  clear(): void {
    getStorage()?.removeItem(STORAGE_KEY);
  },
};
