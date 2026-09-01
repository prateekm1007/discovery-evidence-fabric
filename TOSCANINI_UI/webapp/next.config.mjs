/** Next.js config — the frontend NEVER imports Python; it talks to the
 * long-running engine service through the clean job API only (R389 Phase 7).
 * In dev, /api/* is proxied to the local engine service (port 8788).
 * In prod (Vercel), ENGINE_API env points at the deployed engine service. */
const ENGINE_API = process.env.ENGINE_API || "http://127.0.0.1:8788";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${ENGINE_API}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
