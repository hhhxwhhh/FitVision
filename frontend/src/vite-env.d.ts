/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly BASE_URL: string
  readonly MODE: string
  readonly DEV: boolean
  readonly PROD: boolean
  /** Base URL of the Django API, e.g. `/api` or `https://api.example.com/api`. */
  readonly VITE_API_BASE_URL?: string
  /** Backend origin used by the Vite dev-server proxy. */
  readonly VITE_DEV_PROXY_TARGET?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
