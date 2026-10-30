import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface TileProps {
  title: string;
  subtitle?: string; // caminho discreto, em fonte monoespaçada, ex.: "/trilhas"
  to?: string;
  onClick?: () => void;
  badge?: ReactNode;
  footer?: ReactNode;
  accent?: boolean; // destaca o cartão ativo com a barra em degradê na base
  progress?: number; // 0..100, mostra a barra na base
  wide?: boolean;
  className?: string;
  children?: ReactNode;
}

/** Cartão de painel inicial: título, caminho discreto, selo de estado e rodapé. */
export function Tile({
  title,
  subtitle,
  to,
  onClick,
  badge,
  footer,
  accent,
  progress,
  wide,
  className = "",
  children,
}: TileProps) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[17px] font-semibold leading-snug tracking-tight text-white">{title}</h3>
          {subtitle && <p className="mt-1 font-mono text-[12px] text-slate-500">{subtitle}</p>}
        </div>
        {badge}
      </div>
      {children && <div className="mt-4 text-[14px] leading-relaxed text-slate-400">{children}</div>}
      <div className="mt-auto flex items-center justify-between gap-3 pt-5">{footer}</div>
      {progress !== undefined && (
        <div className="absolute inset-x-0 bottom-0 h-[3px] overflow-hidden rounded-b-[22px] bg-white/[0.06]">
          <div
            className="h-full bg-gradient-to-r from-brand-500 via-violet-500 to-ios-orange transition-[width] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </>
  );

  const base = `group relative flex min-h-[168px] flex-col overflow-hidden rounded-[22px] border border-line p-5 text-left transition duration-300 ${
    wide ? "md:col-span-2" : ""
  } ${accent ? "bg-white/[0.07]" : "bg-white/[0.035]"} hover:-translate-y-0.5 hover:border-white/15 hover:bg-white/[0.07] active:scale-[0.99] ${className}`;

  if (to) {
    return (
      <Link to={to} className={base}>
        {body}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={base}>
      {body}
    </button>
  );
}

/** Selo de estado, no estilo "LIVE" da referência. */
export function StatePill({ children, tone = "live" }: { children: ReactNode; tone?: "live" | "info" | "neutral" }) {
  const styles = {
    live: "bg-[#ffffff]/90 text-black",
    info: "bg-brand-500/20 text-brand-200",
    neutral: "bg-white/[0.08] text-slate-300",
  };
  return (
    <span
      className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${styles[tone]}`}
    >
      {children}
    </span>
  );
}

/** Avatar circular com iniciais, usado para idiomas e pessoas. */
export function Avatar({ label, tone = "from-brand-500 to-violet-500" }: { label: string; tone?: string }) {
  return (
    <span
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${tone} text-[11px] font-semibold text-on-accent`}
    >
      {label}
    </span>
  );
}
