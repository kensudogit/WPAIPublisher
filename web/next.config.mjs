import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname),
  // 複数 HTML アップロード用（既定 ~10MB だと途中で切れることがある）
  experimental: {
    middlewareClientMaxBodySize: '50mb',
    proxyClientMaxBodySize: '50mb',
  },
  serverActions: {
    bodySizeLimit: '50mb',
  },
}

export default nextConfig
