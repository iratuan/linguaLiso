import type { CSSProperties, ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { ServiceState } from "../hooks/useServiceStatus";

/**
 * Contêiner padrão de todas as telas: mesma margem lateral, mesma largura de leitura
 * e mesmo espaçamento vertical. `wide` é usado onde há grades (trilhas, progresso).
 */
export function PageContainer({
  children,
  wide = false,
  className = "",
}: {
  children: ReactNode;
  wide?: boolean;
  className?: string;
}) {
  return (
    <div className={`mx-auto w-full px-8 pb-24 pt-10 ${wide ? "max-w-5xl" : "max-w-3xl"} ${className}`}>{children}</div>
  );
}

/** Grupo de linhas no estilo “Ajustes” do macOS/iOS: título discreto e um bloco arredondado. */
export function SettingsGroup({ title, footer, children }: { title: string; footer?: ReactNode; children: ReactNode }) {
  return (
    <section className="animate-rise flex flex-col gap-2">
      <h2 className="px-4 text-[13px] font-medium uppercase tracking-[0.06em] text-slate-500">{title}</h2>
      <div className="divide-y divide-line overflow-hidden rounded-[18px] border border-line bg-white/[0.035]">
        {children}
      </div>
      {footer && <p className="px-4 text-[13px] leading-relaxed text-slate-500">{footer}</p>}
    </section>
  );
}

/** Linha de configuração: rótulo e descrição à esquerda, controle à direita. */
export function SettingRow({
  label,
  description,
  control,
  htmlFor,
}: {
  label: string;
  description?: string;
  control: ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="flex min-h-[56px] items-center justify-between gap-6 px-4 py-3">
      <div className="min-w-0">
        <label htmlFor={htmlFor} className="block text-[15px] text-slate-100">
          {label}
        </label>
        {description && <p className="mt-0.5 text-[13px] leading-snug text-slate-500">{description}</p>}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

/** Controle deslizante com o trilho preenchido até o valor atual. */
export function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  className = "w-44",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  className?: string;
}) {
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <input
      type="range"
      aria-label={label}
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className={className}
      style={{ "--fill": `${Math.min(100, Math.max(0, fill))}%` } as CSSProperties}
    />
  );
}

/** Medidor de voz durante a gravação: barras que acompanham o volume e o tempo decorrido. */
export function VoiceMeter({ level, elapsedMs, maxMs }: { level: number; elapsedMs: number; maxMs: number }) {
  const seconds = Math.floor(elapsedMs / 1000);
  const remaining = Math.max(0, Math.ceil((maxMs - elapsedMs) / 1000));
  // Cada barra reage a uma faixa diferente do nível, para o desenho parecer natural.
  const weights = [0.55, 0.85, 1, 0.8, 0.6];
  return (
    <div className="flex items-center gap-3" aria-hidden>
      <div className="flex h-5 items-end gap-[3px]">
        {weights.map((w, i) => (
          <span
            key={i}
            className="w-[3px] rounded-full bg-ios-red transition-[height] duration-150 ease-out"
            style={{ height: `${Math.max(15, Math.min(100, level * w * 140))}%` }}
          />
        ))}
      </div>
      <span className="font-mono text-[12px] tabular-nums text-slate-400">
        {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
        {remaining <= 10 && <span className="text-ios-orange"> · {remaining}s</span>}
      </span>
    </div>
  );
}

/** Interruptor no estilo iOS para opções ligadas/desligadas. */
export function Switch({
  checked,
  onChange,
  label,
  disabled = false,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-[31px] w-[51px] shrink-0 rounded-full transition-colors duration-300 disabled:opacity-40 ${
        checked ? "bg-ios-green" : "bg-white/[0.16]"
      }`}
    >
      <span
        className={`absolute left-[2px] top-[2px] h-[27px] w-[27px] rounded-full bg-[#ffffff] shadow-md transition-transform duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
          checked ? "translate-x-[20px]" : "translate-x-0"
        }`}
      />
    </button>
  );
}

/** Controle segmentado acessível (role=tablist) para alternar entre poucas opções. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled = false,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="segmented">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          disabled={disabled}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Card({
  children,
  className = "",
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <section className={`card animate-rise ${interactive ? "card-interactive" : ""} ${className}`}>{children}</section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
  path,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  eyebrow?: string;
  path?: string; // caminho discreto, como nos cartões do início: "/trilhas"
}) {
  return (
    <header className="animate-rise flex flex-wrap items-end justify-between gap-6 pb-8">
      <div className="min-w-0">
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h1 className="title-large">{title}</h1>
        {path && <p className="mt-2 font-mono text-[12px] text-slate-500">{path}</p>}
        {subtitle && <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function ErrorBanner({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="animate-rise mb-4 flex items-start gap-3 rounded-2xl border border-ios-red/30 bg-ios-red/10 px-4 py-3 text-[14px] text-rose-100"
    >
      <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-ios-red" />
      <p className="flex-1 leading-relaxed">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-lg leading-none text-rose-200 hover:text-white"
          aria-label="Fechar aviso"
        >
          ×
        </button>
      )}
    </div>
  );
}

export function InfoBanner({ children }: { children: ReactNode }) {
  return (
    <div className="animate-rise flex items-start gap-3 rounded-2xl border border-ios-orange/25 bg-ios-orange/10 px-4 py-3 text-[14px] text-amber-100">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ios-orange" />
      <div className="flex-1 leading-relaxed">{children}</div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-[14px] text-slate-400">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </span>
  );
}

const STATE_STYLE: Record<ServiceState, { dot: string; text: string }> = {
  ok: { dot: "bg-ios-green shadow-[0_0_8px_rgba(48,209,88,0.7)]", text: "text-slate-200" },
  warning: { dot: "bg-ios-orange shadow-[0_0_8px_rgba(255,159,10,0.6)]", text: "text-amber-200" },
  down: { dot: "bg-ios-red shadow-[0_0_8px_rgba(255,69,58,0.6)]", text: "text-rose-200" },
  checking: { dot: "bg-slate-500 animate-pulse", text: "text-slate-400" },
};

export function StatusPill({ label, state, title }: { label: string; state: ServiceState; title?: string }) {
  const style = STATE_STYLE[state];
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-2 rounded-full border border-line bg-white/[0.05] px-3 py-1 text-[12px] font-medium ${style.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
      {label}
    </span>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "bad" | "info" | "warn";
}) {
  const tones = {
    neutral: "bg-white/[0.08] text-slate-300",
    good: "bg-ios-green/15 text-emerald-300",
    bad: "bg-ios-red/15 text-rose-300",
    info: "bg-brand-500/15 text-brand-300",
    warn: "bg-ios-orange/15 text-amber-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[12px] font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white/[0.07] text-brand-300">
        {icon}
      </div>
      <h3 className="text-[17px] font-semibold text-slate-100">{title}</h3>
      {children && <div className="max-w-md text-[14px] leading-relaxed text-slate-400">{children}</div>}
    </div>
  );
}

export function OkMark({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-[14px] ${ok ? "text-emerald-300" : "text-rose-300"}`}>
      {ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
      {label}
    </span>
  );
}
