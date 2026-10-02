interface StoredTokens {
  accessToken: string;
}

let sessionToken: StoredTokens | null = null;

/** Access tokens are memory-only; FastAPI owns the HttpOnly refresh cookie. */
export const tokenStorage = {
  getTokens(): StoredTokens | null {
    return sessionToken;
  },

  setTokens(tokens: StoredTokens): void {
    sessionToken = tokens;
  },

  setAccessToken(accessToken: string): void {
    sessionToken = { accessToken };
  },

  clear(): void {
    sessionToken = null;
  },
};
