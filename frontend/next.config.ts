import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep the live development compiler isolated from `next build` output.
  // Running both against `.next` can leave the browser hydrating with stale chunks.
  distDir: process.env.NEXT_DIST_DIR ?? (process.env.NODE_ENV === "development" ? ".next-dev" : ".next"),
  output: "standalone",
  turbopack: {
    root: process.cwd(),
  },
  async redirects() {
    return [{ source: "/experiences", destination: "/destinations", permanent: true }];
  },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};

export default nextConfig;
