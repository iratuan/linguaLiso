import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Diagnostics } from "../lib/types";

export type ServiceState = "ok" | "warning" | "down" | "checking";

export interface ServiceStatus {
  backend: ServiceState;
  llm: ServiceState;
  speech: ServiceState;
  details: Diagnostics | null;
  refresh: () => void;
}

const POLL_MS = 15_000;

/** Consulta o diagnóstico do backend periodicamente para os indicadores da barra superior. */
export function useServiceStatus(): ServiceStatus {
  const [details, setDetails] = useState<Diagnostics | null>(null);
  const [backend, setBackend] = useState<ServiceState>("checking");

  const refresh = useCallback(() => {
    api
      .diagnostics()
      .then((data) => {
        setDetails(data);
        setBackend("ok");
      })
      .catch(() => {
        setDetails(null);
        setBackend("down");
      });
  }, []);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const llm: ServiceState = !details
    ? backend === "down"
      ? "down"
      : "checking"
    : !details.llm.reachable
      ? "down"
      : details.llm.model_installed
        ? "ok"
        : "warning";

  const speech: ServiceState = !details
    ? backend === "down"
      ? "down"
      : "checking"
    : !details.speech.reachable
      ? "down"
      : details.speech.stt_ready && details.speech.tts_ready
        ? "ok"
        : "warning";

  return { backend, llm, speech, details, refresh };
}
