/** Next.js config — the frontend NEVER imports Python; it talks to the
 * long-running engine service through the clean job API only (R389 Phase 7).
 * All fetch paths are same-origin relative, so two deployment shapes work
 * from this one codebase (R391):
 *   1. Vercel: /api/* is proxied to the engine service (ENGINE_API env).
 *   2. Same-origin static export (Render engine host): NEXT_OUTPUT=export
 *      builds ./out; the engine serves it and /api/* resolves to itself —
 *      no proxy needed. rewrites() are ignored in export mode. */
const ENGINE_API = process.env.ENGINE_API || "http://127.0.0.1:8788";
const EXPORT = process.env.NEXT_OUTPUT === "export";

/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(EXPORT ? { output: "export", trailingSlash: true } : {}),
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
