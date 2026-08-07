import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },
  allowedDevOrigins: [
    "127.0.0.1",
    "*.replit.dev",
    "*.riker.replit.dev",
    "*.picard.replit.dev",
    "*.kirk.replit.dev",
    "*.spock.replit.dev",
    "*.janeway.replit.dev",
  ],

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "ui.shadcn.com" },
      { protocol: "https", hostname: "images.unsplash.com" },
    ],
    formats: ["image/webp", "image/avif"],
  },

  async rewrites() {
    return [
      { source: "/api/dashboard/:path*", destination: "http://127.0.0.1:8000/api/dashboard/:path*" },
      { source: "/v1/:path*",            destination: "http://127.0.0.1:8000/v1/:path*" },
      { source: "/threads",              destination: "http://127.0.0.1:8000/threads" },
      { source: "/chat",                 destination: "http://127.0.0.1:8000/chat" },
      { source: "/status",               destination: "http://127.0.0.1:8000/status" },
      { source: "/healthz",              destination: "http://127.0.0.1:8000/healthz" },
    ];
  },

  async redirects() {
    return [
      { source: "/home", destination: "/dashboard", permanent: true },
      { source: "/", destination: "/dashboard", permanent: false },
    ];
  },
};

export default nextConfig;
