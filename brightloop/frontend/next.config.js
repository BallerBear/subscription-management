/** @type {import('next').NextConfig} */
// Browser calls /api/* on Next; Next forwards to FastAPI and strips the /api prefix,
// so /api/health -> http://127.0.0.1:8000/health
const apiUrl = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
};

module.exports = nextConfig;
