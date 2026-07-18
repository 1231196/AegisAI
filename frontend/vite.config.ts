import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Read .env files so docker-compose / local-uvicorn dev can switch backends
  // without editing this file. `VITE_BACKEND_URL` is the canonical knob.
  // Restricting the prefix filter to ``VITE_`` keeps unrelated env vars
  // (PATH, AWS_*, etc.) from accidentally overriding the proxy target.
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const defaultBackend =
    env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: false,
      proxy: {
        "/api": {
          // In dev the Vite proxy forwards /api/* to the FastAPI backend.
          // The target MUST be an explicit IPv4 literal: macOS resolves
          // ``localhost`` to ``::1`` first, which can collide with a
          // stale docker-compose backend mapped to ``[::]:8000``. Pinning
          // to ``127.0.0.1`` routes deterministically to local uvicorn
          // when the dev session is running on the host.
          target: defaultBackend,
          changeOrigin: true,
          secure: false,
          // Strip the ``/api`` prefix so the backend's routers mount at
          // ``/auth/...`` (not ``/api/auth/...``). The lookahead anchors
          // the strip to ``/`` or end-of-path so bare ``/api`` becomes
          // ``/`` and ``/api/`` becomes ``/`` (not the empty string).
          rewrite: (path) => path.replace(/^\/api(?=\/|$)/, "") || "/",
        },
      },
    },
  };
});
