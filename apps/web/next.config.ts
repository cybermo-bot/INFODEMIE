import type { NextConfig } from "next";
const config: NextConfig = {
  distDir: process.env.APP_ENV === "local" ? ".next-local" : ".next",
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination:
          (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000") +
          "/api/:path*",
      },
    ];
  },
};
export default config;
