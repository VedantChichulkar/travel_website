interface StoredTokens {
  accessToken: string;
}

let sessionToken: StoredTokens | null = null;

/** Access tokens are memory-only; FastAPI owns the HttpOnly refresh cookie. */
export const tokenStorage = {
  get(): StoredTokens | null {
    return sessionToken;
  },

  set(tokens: StoredTokens): void {
    sessionToken = tokens;
  },

  updateAccessToken(accessToken: string): void {
    sessionToken = { accessToken };
  },

  clear(): void {
    sessionToken = null;
  },
};
