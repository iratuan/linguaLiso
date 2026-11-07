// Aparência da interface: transparência (0 a 80%) e tema (escuro, papel ou pixel 8 bits).
// A transparência vira a variável --ui-alpha, lida pelo CSS. O tema vira o atributo data-theme.

export type AppTheme = "escuro" | "papel" | "pixel";

export const DEFAULT_TRANSPARENCY = 45;

export const THEME_LABELS: Record<AppTheme, string> = {
  escuro: "Escuro",
  papel: "Papel (Kindle)",
  pixel: "Pixel 8 bits",
};

/** Aplica a aparência salva, ou a prévia na tela de ajustes, a todo o app. */
export function applyAppearance({ transparency, theme }: { transparency: number; theme: AppTheme }): void {
  const root = document.documentElement;
  const clamped = Math.min(80, Math.max(0, transparency));
  let alpha = (100 - clamped) / 100;
  // A página de papel precisa ser quase opaca para parecer papel, mesmo com transparência alta.
  if (theme === "papel") alpha = Math.max(alpha, 0.92);
  // O pixel 8 bits é sólido: vidro translúcido não combina com ele.
  if (theme === "pixel") alpha = 1;
  root.style.setProperty("--ui-alpha", alpha.toFixed(2));
  root.dataset.theme = theme;
}
