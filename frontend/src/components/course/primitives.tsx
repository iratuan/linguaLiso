import { Fragment, type ReactNode } from "react";

/** Anel de progresso animado (SVG). */
export function ProgressRing({
  percent,
  size = 88,
  stroke = 8,
  label,
}: {
  percent: number;
  size?: number;
  stroke?: number;
  label?: ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#ring-gradient)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.2,0.8,0.2,1)" }}
        />
        <defs>
          <linearGradient id="ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#0a84ff" />
            <stop offset="100%" stopColor="#bf5af2" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{label}</div>
    </div>
  );
}

/**
 * Renderiza um subconjunto de Markdown com elementos React (sem HTML bruto):
 * parágrafos, listas com "- ", **negrito** e *itálico*.
 */
export function RichText({ source, className = "" }: { source: string; className?: string }) {
  const blocks = source
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);
  return (
    <div className={`flex flex-col gap-4 text-[16px] leading-[1.65] text-slate-300 ${className}`}>
      {blocks.map((block, i) => {
        const lines = block
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean);
        if (lines.every((l) => l.startsWith("- "))) {
          return (
            <ul key={i} className="flex flex-col gap-2">
              {lines.map((l, j) => (
                <li key={j} className="flex gap-3">
                  <span className="mt-[0.6em] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" aria-hidden />
                  <span>{inline(l.slice(2))}</span>
                </li>
              ))}
            </ul>
          );
        }
        return <p key={i}>{inline(lines.join(" "))}</p>;
      })}
    </div>
  );
}

/** Texto curto com **negrito** e *itálico*, sem blocos. */
export function InlineText({ text }: { text: string }) {
  return <>{inline(text)}</>;
}

const INLINE_RE = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;

function inline(text: string): ReactNode {
  return text.split(INLINE_RE).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={i} className="text-brand-200 not-italic">
          {part.slice(1, -1)}
        </em>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}
