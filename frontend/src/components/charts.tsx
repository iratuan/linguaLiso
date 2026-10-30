import { useId, useMemo, useState, type MouseEvent, type ReactNode } from "react";

export interface Point {
  label: string; // data legível, ex.: "28/10"
  value: number | null;
}

const W = 640;
const H = 220;
const PAD = { top: 16, right: 12, bottom: 28, left: 40 };

function formatTick(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/**
 * Caminho suave (Catmull-Rom convertido em Bézier). Os pontos de controle são limitados
 * ao intervalo entre os dois pontos do trecho, para a curva nunca ultrapassar os dados.
 */
export function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M${points[0].x},${points[0].y}`;
  const clamp = (v: number, a: number, b: number) => Math.min(Math.max(v, Math.min(a, b)), Math.max(a, b));
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = clamp(p1.y + (p2.y - p0.y) / 6, p1.y, p2.y);
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = clamp(p2.y - (p3.y - p1.y) / 6, p1.y, p2.y);
    d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`;
  }
  return d;
}

/** Escala com marcos "redondos" (1, 2, 2,5, 5 × 10ⁿ), para que os rótulos do eixo sejam legíveis. */
export function niceScale(
  lo: number,
  hi: number,
  count = 4,
  integer = false,
): { lo: number; hi: number; ticks: number[] } {
  const span = hi - lo || 1;
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  let step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw * 2;
  // Contagens (lições, palavras) nunca têm marcos fracionários.
  if (integer && step < 1) step = 1;
  const niceLo = Math.floor(lo / step) * step;
  // Intervalo degenerado (todos os valores iguais): garante ao menos dois marcos no eixo.
  const niceHi = Math.max(Math.ceil(hi / step) * step, niceLo + step);
  const ticks: number[] = [];
  for (let t = niceLo; t <= niceHi + step / 2; t += step) ticks.push(Math.round(t * 1000) / 1000);
  return { lo: niceLo, hi: niceHi, ticks };
}

/** Curva com área e dica ao passar o mouse. Valores nulos quebram a linha (sem dados). */
export function LineChart({
  points,
  color = "#0a84ff",
  yMin,
  yMax,
  integer = false,
  suffix = "",
  ariaLabel,
  emptyText = "Ainda não há dados suficientes para este período.",
}: {
  points: Point[];
  color?: string;
  yMin?: number;
  yMax?: number;
  integer?: boolean;
  suffix?: string;
  ariaLabel: string;
  emptyText?: string;
}) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);

  const scale = useMemo(() => {
    const nice = niceScale(
      yMin ?? (values.length ? Math.min(...values) : 0),
      yMax ?? (values.length ? Math.max(...values) : 1),
      4,
      integer,
    );
    const { lo, hi, ticks } = nice;
    const span = hi - lo || 1;
    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const xOf = (i: number) => PAD.left + (points.length <= 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
    const yOf = (v: number) => PAD.top + innerH - ((v - lo) / span) * innerH;
    return { lo, hi, ticks, xOf, yOf };
  }, [points, values, yMin, yMax, integer]);

  if (values.length === 0) {
    return <EmptyChart text={emptyText} />;
  }

  // Divide a série em trechos contínuos (um por sequência de valores não nulos).
  const segments: { x: number; y: number; i: number }[][] = [];
  let current: { x: number; y: number; i: number }[] = [];
  points.forEach((p, i) => {
    if (p.value === null) {
      if (current.length) segments.push(current);
      current = [];
    } else {
      current.push({ x: scale.xOf(i), y: scale.yOf(p.value), i });
    }
  });
  if (current.length) segments.push(current);

  const ticks = scale.ticks;
  const labelIdx = [0, Math.floor((points.length - 1) / 2), points.length - 1].filter(
    (v, i, arr) => arr.indexOf(v) === i,
  );

  const onMove = (event: MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * W;
    const innerW = W - PAD.left - PAD.right;
    const idx = Math.round(((x - PAD.left) / innerW) * (points.length - 1));
    setHover(Math.min(points.length - 1, Math.max(0, idx)));
  };

  const hovered = hover !== null ? points[hover] : null;

  return (
    <div className="relative w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label={ariaLabel}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={scale.yOf(t)}
              y2={scale.yOf(t)}
              stroke="rgba(255,255,255,0.07)"
            />
            <text x={PAD.left - 8} y={scale.yOf(t) + 4} textAnchor="end" fontSize="11" fill="rgba(255,255,255,0.4)">
              {formatTick(t)}
            </text>
          </g>
        ))}

        {segments.map((seg, k) => {
          const line = smoothPath(seg);
          const area = `${line} L${seg[seg.length - 1].x},${PAD.top + (H - PAD.top - PAD.bottom)} L${seg[0].x},${PAD.top + (H - PAD.top - PAD.bottom)} Z`;
          return (
            <g key={k}>
              {seg.length > 1 && <path d={area} fill={`url(#${gradientId})`} />}
              <path
                d={line}
                fill="none"
                stroke={color}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          );
        })}

        {segments.flat().map((pt) => (
          <circle
            key={pt.i}
            cx={pt.x}
            cy={pt.y}
            r={hover === pt.i ? 5 : values.length <= 3 ? 4.5 : 2.5}
            fill={color}
            stroke="#0b0b0f"
            strokeWidth="1.5"
            style={{ transition: "r 150ms" }}
          />
        ))}

        {hover !== null && (
          <line
            x1={scale.xOf(hover)}
            x2={scale.xOf(hover)}
            y1={PAD.top}
            y2={H - PAD.bottom}
            stroke="rgba(255,255,255,0.18)"
            strokeDasharray="3 4"
          />
        )}

        {labelIdx.map((i) => (
          <text
            key={i}
            x={scale.xOf(i)}
            y={H - 8}
            textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}
            fontSize="11"
            fill="rgba(255,255,255,0.4)"
          >
            {points[i].label}
          </text>
        ))}
      </svg>

      {hovered && hovered.value !== null && (
        <Tooltip
          x={(scale.xOf(hover ?? 0) / W) * 100}
          title={hovered.label}
          value={`${formatTick(hovered.value)}${suffix}`}
          color={color}
        />
      )}
    </div>
  );
}

/** Barras diárias (ex.: frases por dia), com dica ao passar o mouse. */
export function BarChart({
  points,
  color = "#bf5af2",
  ariaLabel,
  suffix = "",
  max: fixedMax,
  emptyText = "Nenhuma atividade neste período.",
}: {
  points: Point[];
  color?: string;
  ariaLabel: string;
  suffix?: string;
  max?: number;
  emptyText?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = fixedMax ?? Math.max(0, ...points.map((p) => p.value ?? 0));
  if (points.every((p) => !p.value)) return <EmptyChart text={emptyText} />;

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const slot = innerW / points.length;
  const barW = Math.max(2, slot * 0.62);
  const labelIdx = [0, Math.floor((points.length - 1) / 2), points.length - 1].filter(
    (v, i, arr) => arr.indexOf(v) === i,
  );

  return (
    <div className="relative w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full overflow-visible"
        role="img"
        aria-label={ariaLabel}
        onMouseLeave={() => setHover(null)}
      >
        {[0, 1, 2].map((k) => {
          const y = PAD.top + (innerH * k) / 2;
          return <line key={k} x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="rgba(255,255,255,0.07)" />;
        })}
        {points.map((p, i) => {
          const v = p.value ?? 0;
          const h = (v / max) * innerH;
          const x = PAD.left + i * slot + (slot - barW) / 2;
          const y = PAD.top + innerH - h;
          return (
            <g key={i} onMouseEnter={() => setHover(i)}>
              <rect x={PAD.left + i * slot} y={PAD.top} width={slot} height={innerH} fill="transparent" />
              <rect
                x={x}
                y={y}
                width={barW}
                height={Math.max(v > 0 ? 3 : 0, h)}
                rx={Math.min(barW / 2, 4)}
                fill={color}
                opacity={hover === null || hover === i ? 0.95 : 0.35}
                style={{ transition: "opacity 150ms" }}
              />
            </g>
          );
        })}
        {labelIdx.map((i) => (
          <text
            key={i}
            x={PAD.left + i * slot + slot / 2}
            y={H - 8}
            textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}
            fontSize="11"
            fill="rgba(255,255,255,0.4)"
          >
            {points[i].label}
          </text>
        ))}
      </svg>
      {hover !== null && points[hover].value !== null && (
        <Tooltip
          x={((PAD.left + hover * slot + slot / 2) / W) * 100}
          title={points[hover].label}
          value={`${formatTick(points[hover].value ?? 0)}${suffix}`}
          color={color}
        />
      )}
    </div>
  );
}

function Tooltip({ x, title, value, color }: { x: number; title: string; value: string; color: string }) {
  return (
    <div
      className="pointer-events-none absolute top-0 -translate-x-1/2 rounded-xl border border-line bg-surface-2/95 px-3 py-1.5 text-center shadow-xl backdrop-blur-xl"
      style={{ left: `${Math.min(92, Math.max(8, x))}%` }}
    >
      <p className="text-[11px] text-slate-400">{title}</p>
      <p className="text-[14px] font-semibold text-white" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

function EmptyChart({ text }: { text: string }): ReactNode {
  return (
    <div className="flex h-[220px] items-center justify-center rounded-2xl border border-dashed border-white/10 text-center text-[14px] text-slate-500">
      {text}
    </div>
  );
}
