import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Server-side address of the FastAPI app. The browser only talks to /api on this
// origin, so session cookies stay first-party and no key ever reaches the client.
const apiOrigin = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  transpilePackages: ["@pnsi/api-client"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
export default withNextIntl(nextConfig);
