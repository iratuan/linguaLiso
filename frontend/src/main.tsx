import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

// Exposto pelo preload do Electron (electron/preload.cjs).
declare global {
  interface Window {
    englishTeacher?: {
      platform: string;
      appVersion: string;
      chat?: { popout: () => Promise<void>; restore: () => Promise<void> };
    };
  }
}

// No app desktop no Windows, a janela tem material Mica: o fundo da página fica transparente
// para o vidro aparecer atrás da barra lateral (ver regras .native-backdrop em index.css).
if (window.englishTeacher?.platform === "win32") {
  document.documentElement.classList.add("native-backdrop");
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
