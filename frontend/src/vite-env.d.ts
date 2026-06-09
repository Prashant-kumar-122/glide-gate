/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

declare module '*.css' {
  const content: string
  export default content
}

// Injected by vite-plugin-pwa at build time — the precache manifest list
declare const __WB_MANIFEST: Array<{ url: string; revision: string | null }>
