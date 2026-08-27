/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for Docker standalone deployment (Dockerfile copies .next/standalone)
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.r2.cloudflarestorage.com',
      },
      {
        protocol: 'https',
        hostname: '*.tile.openstreetmap.org',
      },
    ],
  },
  // Allows importing leaflet CSS from node_modules
  transpilePackages: ['leaflet', 'react-leaflet'],
};

export default nextConfig;
