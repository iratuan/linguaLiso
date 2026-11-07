import { useCallback, useEffect, useState } from "react";
import { api, describeError } from "../lib/api";
import type { LlmProvider, OllamaStatus, StorageReport } from "../lib/types";
import { ErrorBanner, SettingRow, SettingsGroup } from "./ui";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : 1).replace(".", ",")} ${units[i]}`;
}

/** Grupo "Modelos de IA" e "Espaço": reúne o que a tela de Conversa não mostra sozinha. */
export function ModelSettings({ onProvidersChanged }: { onProvidersChanged: () => void }) {
  return (
    <>
      <OllamaSection />
      <CloudSection onChanged={onProvidersChanged} />
      <StorageSection />
    </>
  );
}

// ----- Ollama ----------------------------------------------------------------

function OllamaSection() {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const downloading = status?.download.status === "downloading";

  const load = useCallback(() => {
    api
      .ollamaStatus()
      .then((s) => setStatus(s))
      .catch((e) => setError(describeError(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Enquanto baixa, atualiza o progresso a cada 2 s.
  useEffect(() => {
    if (!downloading) return;
    const id = window.setInterval(load, 2000);
    return () => window.clearInterval(id);
  }, [downloading, load]);

  const pull = async (model: string) => {
    setError(null);
    try {
      await api.pullModel(model);
      load();
    } catch (e) {
      setError(describeError(e));
    }
  };

  const ollamaState = !status
    ? "Verificando…"
    : status.reachable
      ? "Rodando"
      : status.binary_found
        ? "Instalado, mas parado (o app tenta iniciar ao abrir)"
        : "Não instalado";

  return (
    <SettingsGroup
      title="Modelos locais (Ollama)"
      footer={
        status && !status.binary_found
          ? "Sem o Ollama, use um provedor na nuvem abaixo. Para instalar, rode scripts\\iniciar.ps1 e confirme a instalação pelo winget."
          : "Modelos do Ollama rodam no seu computador e não custam tokens. Baixar pode levar vários GB."
      }
    >
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      <SettingRow label="Ollama" description={ollamaState} control={<span className="text-[13px] text-slate-400">{status?.reachable ? "●" : "○"}</span>} />
      {status?.suggested.map((s) => {
        const isThis = downloading && status.download.model === s.model;
        const percent = isThis ? status.download.percent : null;
        const control = s.installed ? (
          <span className="text-[13px] text-ios-green">Instalado</span>
        ) : isThis ? (
          <span className="text-[13px] text-slate-300">Baixando {percent !== null ? `${percent.toFixed(0)}%` : "…"}</span>
        ) : (
          <button
            type="button"
            disabled={!status.reachable || downloading}
            onClick={() => void pull(s.model)}
            className="rounded-full bg-brand-500 px-4 py-1.5 text-[13px] font-medium text-white transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Baixar
          </button>
        );
        return (
          <SettingRow
            key={s.model}
            label={s.model}
            description={s.role === "principal" ? "Modelo principal (recomendado)" : "Modelo leve, para máquinas mais fracas"}
            control={control}
          />
        );
      })}
      {status?.download.status === "error" && (
        <p className="px-4 py-3 text-[13px] text-ios-red">{status.download.error}</p>
      )}
    </SettingsGroup>
  );
}

// ----- Provedores na nuvem ---------------------------------------------------

function CloudSection({ onChanged }: { onChanged: () => void }) {
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .providers()
      .then(setProviders)
      .catch((e) => setError(describeError(e)));
  }, []);

  return (
    <SettingsGroup
      title="Provedores na nuvem (opcional)"
      footer="Para aulas mais profundas. Mensagens enviadas a estes provedores são cobradas por token. Use o Ollama para o dia a dia e troque só quando quiser uma explicação melhor. A chave fica em backend\.env, neste computador."
    >
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {providers.map((p) => (
        <ProviderRow
          key={p.provider}
          provider={p}
          onSaved={(list) => {
            setProviders(list);
            onChanged();
          }}
          onError={setError}
        />
      ))}
    </SettingsGroup>
  );
}

function ProviderRow({
  provider,
  onSaved,
  onError,
}: {
  provider: LlmProvider;
  onSaved: (list: LlmProvider[]) => void;
  onError: (message: string) => void;
}) {
  const [key, setKey] = useState("");
  const [model, setModel] = useState(provider.model);
  const [busy, setBusy] = useState(false);

  const save = async (apiKey: string | null) => {
    setBusy(true);
    try {
      const list = await api.saveProvider(provider.provider, { api_key: apiKey, model: model.trim() || null });
      setKey("");
      onSaved(list);
    } catch (e) {
      onError(describeError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[15px] text-slate-100">{provider.label}</p>
          <p className="text-[13px] text-slate-500">
            {provider.configured ? `Chave salva (${provider.key_hint})` : "Sem chave: não usado"}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="password"
          aria-label={`Chave ${provider.label}`}
          placeholder={provider.configured ? "Nova chave (opcional)" : "Cole a chave aqui"}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          autoComplete="off"
          className="flex-1 rounded-[10px] border border-line bg-white/[0.05] px-3 py-2 text-[14px] text-slate-100 focus:outline-none"
        />
        <input
          type="text"
          aria-label={`Modelo ${provider.label}`}
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="flex-1 rounded-[10px] border border-line bg-white/[0.05] px-3 py-2 text-[14px] text-slate-100 focus:outline-none"
        />
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy || (!key.trim() && model.trim() === provider.model)}
          onClick={() => void save(key.trim() ? key.trim() : null)}
          className="rounded-full bg-brand-500 px-4 py-1.5 text-[13px] font-medium text-white transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Salvar
        </button>
        {provider.configured && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void save("")}
            className="rounded-full border border-line px-4 py-1.5 text-[13px] text-slate-300 transition hover:bg-white/[0.05] disabled:opacity-40"
          >
            Remover chave
          </button>
        )}
      </div>
    </div>
  );
}

// ----- Espaço em disco -------------------------------------------------------

function StorageSection() {
  const [report, setReport] = useState<StorageReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .storage()
      .then(setReport)
      .catch((e) => setError(describeError(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const biggest = report ? Math.max(1, ...report.groups.map((g) => g.bytes)) : 1;

  return (
    <SettingsGroup
      title="Espaço ocupado"
      footer="O total é o que o programa ocupa nesta pasta. Os modelos do Ollama ficam fora dela e aparecem à parte."
    >
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      <SettingRow
        label="Programa e dados"
        description={report ? formatBytes(report.total_bytes) : "Calculando…"}
        control={
          <button type="button" onClick={load} className="text-[13px] text-brand-300 hover:underline">
            Atualizar
          </button>
        }
      />
      {report?.groups.map((g) => (
        <div key={g.id} className="flex flex-col gap-1.5 px-4 py-3">
          <div className="flex items-center justify-between text-[14px] text-slate-200">
            <span>{g.label}</span>
            <span className="tabular-nums text-slate-400">{formatBytes(g.bytes)}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
            <div className="h-full rounded-full bg-brand-400" style={{ width: `${(100 * g.bytes) / biggest}%` }} />
          </div>
        </div>
      ))}
    </SettingsGroup>
  );
}
