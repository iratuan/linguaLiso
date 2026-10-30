import { PERSONA_LABELS, type TeacherPersona } from "../lib/types";

const SKIN = "#f2c9a0";

/**
 * Avatar de cada personalidade, desenhado em SVG (sem imagens externas).
 * Formal: cabelo grisalho, óculos redondos e gravata borboleta.
 * Descontraído: moletom laranja e cabelo cacheado, com sorriso aberto.
 * Nativo: cabelo espetado, fones de ouvido, piscadela e língua de fora.
 */
export function TeacherAvatar({ persona, size = 40 }: { persona: TeacherPersona; size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 overflow-hidden rounded-full ring-1 ring-white/15"
      style={{ width: size, height: size }}
      title={PERSONA_LABELS[persona]}
    >
      <svg viewBox="0 0 64 64" width={size} height={size} role="img" aria-label={`Professor: ${PERSONA_LABELS[persona]}`}>
        {persona === "formal" && <Formal />}
        {persona === "descontraido" && <Relaxed />}
        {persona === "nativo" && <Native />}
      </svg>
    </span>
  );
}

function Formal() {
  return (
    <>
      <circle cx="32" cy="32" r="32" fill="#1e3a5f" />
      <path d="M10 64 Q12 46 32 46 Q52 46 54 64Z" fill="#2b2f3a" />
      <path d="M28 46 L32 53 L36 46Z" fill="#ffffff" />
      <path d="M27.5 50.5 L32 52.5 L27.5 55Z M36.5 50.5 L32 52.5 L36.5 55Z" fill="#c0392b" />
      <rect x="28" y="37" width="8" height="9" fill={SKIN} />
      <ellipse cx="32" cy="27" rx="13" ry="14.5" fill={SKIN} />
      <path d="M19 24 Q19 11 32 11 Q45 11 45 24 Q41 16 32 16 Q23 16 19 24Z" fill="#c4c8d0" />
      <circle cx="26.5" cy="28" r="4" fill="none" stroke="#222" strokeWidth="1.5" />
      <circle cx="37.5" cy="28" r="4" fill="none" stroke="#222" strokeWidth="1.5" />
      <line x1="30.5" y1="28" x2="33.5" y2="28" stroke="#222" strokeWidth="1.5" />
      <circle cx="26.5" cy="28" r="1.4" fill="#222" />
      <circle cx="37.5" cy="28" r="1.4" fill="#222" />
      <path d="M27.5 36 Q32 38.5 36.5 36" stroke="#8a4b3a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
    </>
  );
}

function Relaxed() {
  return (
    <>
      <circle cx="32" cy="32" r="32" fill="#0f766e" />
      <path d="M12 64 Q14 47 32 47 Q50 47 52 64Z" fill="#f59e0b" />
      <path d="M28 47 L27 53 M36 47 L37 53" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" />
      <rect x="28" y="37" width="8" height="9" fill={SKIN} />
      <ellipse cx="32" cy="27" rx="13" ry="14.5" fill={SKIN} />
      <path d="M19 25 Q18 10 32 10 Q46 10 45 25 Q42 16 32 16 Q24 16 19 25Z" fill="#6b3f1f" />
      <circle cx="27" cy="28" r="1.8" fill="#222" />
      <circle cx="37" cy="28" r="1.8" fill="#222" />
      <circle cx="23.5" cy="34" r="2.2" fill="#f87171" opacity="0.4" />
      <circle cx="40.5" cy="34" r="2.2" fill="#f87171" opacity="0.4" />
      <path d="M26 35 Q32 42 38 35" stroke="#8a4b3a" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    </>
  );
}

function Native() {
  return (
    <>
      <circle cx="32" cy="32" r="32" fill="#7c3aed" />
      <path d="M12 64 Q14 47 32 47 Q50 47 52 64Z" fill="#14b8a6" />
      <path
        d="M18 22 L11 12 L21 16 L23 4 L30 12 L34 3 L38 12 L45 4 L43 16 L53 12 L46 22 Z"
        fill="#1f1f1f"
      />
      <rect x="28" y="37" width="8" height="9" fill={SKIN} />
      <ellipse cx="32" cy="27" rx="13" ry="14.5" fill={SKIN} />
      <path d="M17 29 Q17 12 32 12 Q47 12 47 29" stroke="#111" strokeWidth="3" fill="none" />
      <rect x="13" y="26" width="6" height="9" rx="3" fill="#111" />
      <rect x="45" y="26" width="6" height="9" rx="3" fill="#111" />
      <circle cx="27" cy="28" r="1.8" fill="#222" />
      <path d="M34.5 28 Q37 25.5 39.5 28" stroke="#222" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M26 36 Q32 41 38 36" stroke="#8a4b3a" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M30 39 Q32 45 34 39Z" fill="#f472b6" />
    </>
  );
}
