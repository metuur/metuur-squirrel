/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin override for the dev build (e.g. "http://127.0.0.1:3940"). */
  readonly VITE_SQUIRREL_BACKEND_ORIGIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
