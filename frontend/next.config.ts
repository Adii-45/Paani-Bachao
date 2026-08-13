import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // The CLI path in Next 16.3 can truncate `tsc --showConfig` output under
  // Node 22. Use the same TypeScript compiler API that `npm run typecheck`
  // validates directly, without disabling build-time type errors.
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
