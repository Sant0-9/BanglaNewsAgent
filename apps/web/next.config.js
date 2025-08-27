const path = require("path");
/** @type {import('next').NextConfig} */
const nextConfig = {
  typedRoutes: true, // replaces experimental.typedRoutes
  outputFileTracingRoot: path.join(__dirname, "../.."),
  images: {
    domains: ['localhost'],
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      { source: "/ask", destination: "http://localhost:8000/ask" },
      { source: "/ask/stream", destination: "http://localhost:8000/ask/stream" },
      { source: "/timeline", destination: "http://localhost:8000/timeline" },
    ];
  },
}

module.exports = nextConfig