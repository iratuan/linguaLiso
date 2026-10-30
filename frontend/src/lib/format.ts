import type { Level } from "./types";

export const LEVEL_LABELS: Record<Level, string> = {
  A1: "A1 · Iniciante",
  A2: "A2 · Básico",
  B1: "B1 · Intermediário",
  B2: "B2 · Intermediário superior",
  C1: "C1 · Avançado",
};

export const CATEGORY_LABELS: Record<string, string> = {
  grammar: "Gramática",
  vocabulary: "Vocabulário",
  context: "Contexto",
  spelling: "Ortografia",
  other: "Outros",
};

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function formatRelativeDue(iso: string, now: Date = new Date()): string {
  const due = new Date(iso);
  if (Number.isNaN(due.getTime())) return "";
  const diffMs = due.getTime() - now.getTime();
  if (diffMs <= 0) return "Para revisar agora";
  const hours = Math.round(diffMs / 3_600_000);
  if (hours < 24) return `Revisar em ${hours} h`;
  return `Revisar em ${Math.round(hours / 24)} dia(s)`;
}

export function formatSeconds(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
