import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { api, describeError } from "../lib/api";
import { CATEGORY_LABELS, formatDateTime } from "../lib/format";

import type { Evolution, EvolutionDay, Progress, RecurringError } from "../lib/types";
import { BarChart, LineChart, type Point } from "../components/charts";
import { LevelAnalysisPanel } from "../components/LevelAnalysisPanel";
import { Badge, Card, ErrorBanner, PageContainer, PageHeader, Segmented, Spinner } from "../components/ui";

const RANGES = [
  { value: "14", label: "14 dias" },
  { value: "30", label: "30 dias" },
  { value: "90", label: "90 dias" },
];

const dayLabel = (iso: string) => {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
};

export function ProgressPage() {
  const [range, setRange] = useState("30");
  const [evolution, setEvolution] = useState<Evolution | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [recurring, setRecurring] = useState<RecurringError[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.progress(), api.recurringErrors()])
      .then(([p, r]) => {
        setProgress(p);
        setRecurring(r);
      })
      .catch((e) => setError(describeError(e)));
  }, []);

  useEffect(() => {
    setEvolution(null);
    api
      .evolution(Number(range))
      .then(setEvolution)
      .catch((e) => setError(describeError(e)));
  }, [range]);

  const series = useMemo<EvolutionDay[]>(() => evolution?.series ?? [], [evolution]);
  const points = (key: keyof EvolutionDay): Point[] =>
    series.map((d) => ({ label: dayLabel(d.day), value: (d[key] as number | null) ?? null }));

  if (!progress && !error) {
    return (
      <div className="p-10">
        <Spinner label="Carregando seu progresso…" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer wide>
        <PageHeader
          path="/progresso"
          title="Progresso"
          subtitle="Como você está evoluindo: precisão, fluência e avanço no curso."
          actions={<Segmented label="Período" value={range} onChange={setRange} options={RANGES} />}
        />
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {evolution && (
          <>
            {/* Resumo com a tendência em relação ao período anterior */}
            <div className="grid gap-4 md:grid-cols-4">
              <Summary label="Frases praticadas" value={String(evolution.totals.user_messages)} />
              <Summary
                label="Precisão nas conversas"
                value={fmtPct(evolution.totals.conversation_accuracy)}
                delta={delta(evolution.trend.accuracy, "pts")}
              />
              <Summary
                label="Acerto nos exercícios"
                value={fmtPct(evolution.totals.exercise_accuracy)}
                delta={delta(evolution.trend.exercise_accuracy, "pts")}
              />
              <Summary
                label="Tamanho das frases"
                value={evolution.totals.avg_words === null ? "—" : `${evolution.totals.avg_words} palavras`}
                delta={delta(evolution.trend.avg_words, "palavras")}
              />
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <ChartCard
                title="Curva de aprendizado"
                subtitle="Lições concluídas acumuladas"
                badge={`${evolution.totals.lessons_completed} ${evolution.totals.lessons_completed === 1 ? "concluída" : "concluídas"}`}
              >
                <LineChart
                  ariaLabel="Lições concluídas acumuladas ao longo do tempo"
                  color="#0a84ff"
                  yMin={0}
                  integer
                  points={series.map((d) => ({ label: dayLabel(d.day), value: d.cumulative_lessons }))}
                  emptyText="Conclua sua primeira lição para ver a curva."
                />
              </ChartCard>

              <ChartCard
                title="Precisão nas conversas"
                subtitle="Frases sem correção, por dia"
                badge={fmtPct(evolution.totals.conversation_accuracy)}
              >
                <LineChart
                  ariaLabel="Precisão nas conversas por dia"
                  color="#30d158"
                  yMin={0}
                  yMax={100}
                  suffix="%"
                  points={points("accuracy")}
                  emptyText="Converse com o professor para ver sua precisão."
                />
              </ChartCard>

              <ChartCard
                title="Acerto nos exercícios"
                subtitle="Respostas corretas nas trilhas, por dia"
                badge={fmtPct(evolution.totals.exercise_accuracy)}
              >
                <LineChart
                  ariaLabel="Acerto nos exercícios por dia"
                  color="#ff9f0a"
                  yMin={0}
                  yMax={100}
                  suffix="%"
                  points={points("exercise_accuracy")}
                  emptyText="Responda exercícios de uma trilha para ver seu acerto."
                />
              </ChartCard>

              <ChartCard
                title="Fluência nas frases"
                subtitle="Média de palavras por frase"
                badge={evolution.totals.avg_words === null ? undefined : `${evolution.totals.avg_words} em média`}
              >
                <LineChart
                  ariaLabel="Média de palavras por frase ao longo do tempo"
                  color="#bf5af2"
                  yMin={0}
                  suffix=" palavras"
                  points={points("avg_words")}
                  emptyText="Frases mais longas e completas aparecem aqui conforme você pratica."
                />
              </ChartCard>

              <ChartCard title="Atividade diária" subtitle="Frases enviadas ao professor">
                <BarChart
                  ariaLabel="Frases enviadas por dia"
                  color="#0a84ff"
                  points={points("user_messages")}
                  emptyText="Nenhuma conversa neste período."
                />
              </ChartCard>

              <ChartCard title="Notas das lições" subtitle="Nota de cada lição concluída">
                <BarChart
                  ariaLabel="Nota de cada lição concluída"
                  color="#30d158"
                  max={100}
                  suffix="%"
                  points={evolution.lesson_scores.slice(-20).map((l) => ({
                    label: dayLabel(l.completed_at.slice(0, 10)),
                    value: l.score,
                  }))}
                  emptyText="As notas das lições concluídas aparecem aqui."
                />
              </ChartCard>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <ChartCard title="Vocabulário acumulado" subtitle="Palavras adicionadas no período">
                <LineChart
                  ariaLabel="Vocabulário acumulado no período"
                  color="#64d2ff"
                  yMin={0}
                  integer
                  points={series.map((d) => ({ label: dayLabel(d.day), value: d.cumulative_vocabulary }))}
                  emptyText="As palavras que você aprende nas conversas aparecem aqui."
                />
              </ChartCard>

              <Card>
                <h2 className="mb-4 text-[15px] font-semibold text-white">Erros recorrentes</h2>
                {recurring.length === 0 ? (
                  <p className="text-[14px] text-slate-500">
                    Quando um mesmo erro se repete, ele aparece aqui para você revisar.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {recurring.slice(0, 5).map((item) => (
                      <li
                        key={`${item.corrected_text}-${item.error_category}`}
                        className="rounded-2xl bg-white/[0.04] p-4"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-[15px] font-medium text-emerald-300">{item.corrected_text}</span>
                          <Badge tone="bad">{item.occurrences}×</Badge>
                        </div>
                        {item.explanation_pt && (
                          <p className="mt-1 text-[13px] leading-relaxed text-slate-400">{item.explanation_pt}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>

            {progress && progress.recent_corrections.length > 0 && (
              <Card className="mt-6">
                <h2 className="mb-4 text-[15px] font-semibold text-white">Últimas correções</h2>
                <ul className="divide-y divide-line">
                  {progress.recent_corrections.slice(0, 6).map((c, index) => (
                    <li
                      key={`${c.created_at}-${index}`}
                      className="grid gap-1 py-3 md:grid-cols-[1fr_1fr_auto] md:items-center md:gap-6"
                    >
                      <p className="text-[14px] text-slate-500 line-through">{c.original_text}</p>
                      <p className="text-[14px] text-emerald-300">{c.corrected_text}</p>
                      <p className="text-[12px] text-slate-500">
                        {CATEGORY_LABELS[c.error_category] ?? c.error_category} · {formatDateTime(c.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </>
        )}

        {!evolution && !error && (
          <div className="mt-10">
            <Spinner label="Montando os gráficos…" />
          </div>
        )}
        <LevelAnalysisPanel />
      </PageContainer>
    </div>
  );
}

function fmtPct(value: number | null): string {
  return value === null ? "—" : `${Math.round(value)}%`;
}

/** Variação entre a última semana e a anterior, quando há dados nas duas. */
function delta(trend: { recent: number | null; previous: number | null } | undefined, unit: string) {
  if (!trend || trend.recent === null || trend.previous === null) return null;
  const diff = Math.round((trend.recent - trend.previous) * 10) / 10;
  return { diff, unit };
}

function Summary({
  label,
  value,
  delta: change,
}: {
  label: string;
  value: string;
  delta?: { diff: number; unit: string } | null;
}) {
  const up = (change?.diff ?? 0) > 0;
  const flat = change !== null && change !== undefined && change.diff === 0;
  return (
    <Card>
      <p className="text-[12px] font-medium uppercase tracking-[0.06em] text-slate-500">{label}</p>
      <p className="mt-2 text-[28px] font-semibold tracking-tight text-white">{value}</p>
      {change && (
        <p
          className={`mt-1.5 flex items-center gap-1 text-[12px] ${flat ? "text-slate-500" : up ? "text-ios-green" : "text-ios-orange"}`}
        >
          {flat ? (
            <Minus className="h-3 w-3" />
          ) : up ? (
            <ArrowUpRight className="h-3 w-3" />
          ) : (
            <ArrowDownRight className="h-3 w-3" />
          )}
          {change.diff > 0 ? "+" : ""}
          {change.diff} {change.unit} vs. semana anterior
        </p>
      )}
    </Card>
  );
}

function ChartCard({
  title,
  subtitle,
  badge,
  children,
}: {
  title: string;
  subtitle: string;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[16px] font-semibold text-white">{title}</h2>
          <p className="mt-0.5 text-[13px] text-slate-500">{subtitle}</p>
        </div>
        {badge && <Badge tone="info">{badge}</Badge>}
      </div>
      {children}
    </Card>
  );
}
