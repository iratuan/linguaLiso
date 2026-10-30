import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { api, describeError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { AnalysisSummary, LevelAnalysis, Session } from "../lib/types";
import { Badge, Card, ErrorBanner, InfoBanner, Spinner } from "./ui";

const CRITERIA_LABELS: Record<keyof LevelAnalysis["criteria"], string> = {
  vocabulary: "Vocabulário",
  grammar: "Gramática",
  fluency: "Fluência",
  interaction: "Interação",
  coherence: "Coerência",
};

const CONFIDENCE_TONE = { alta: "good", média: "info", baixa: "warn" } as const;

/**
 * Análise de nível: o professor lê uma conversa e estima o nível CEFR, com pontos de melhoria
 * que citam trechos reais da sua fala. Só é mostrado o que passou pelas verificações do app.
 */
export function LevelAnalysisPanel() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[] | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [chosen, setChosen] = useState<number | "">("");
  const [current, setCurrent] = useState<LevelAnalysis | null>(null);
  const [busy, setBusy] = useState<"analyze" | "open" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listAnalyses()
      .then((data) => setAnalyses(data.analyses))
      .catch((e) => setError(describeError(e)));
    api
      .listSessions()
      .then((list) => {
        const withMessages = list.filter((s) => (s.message_count ?? 0) > 0);
        setSessions(withMessages);
        if (withMessages[0]) setChosen(withMessages[0].id);
      })
      .catch(() => undefined);
  }, []);

  const analyze = async () => {
    if (chosen === "") return;
    setBusy("analyze");
    setError(null);
    try {
      const result = await api.analyzeSession(chosen);
      setCurrent(result);
      setAnalyses((await api.listAnalyses()).analyses ?? []);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const open = async (id: number) => {
    setBusy("open");
    setError(null);
    try {
      setCurrent(await api.getAnalysis(id));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="mt-12" aria-labelledby="level-title">
      <div className="mb-5 px-1">
        <p className="eyebrow">Análise de nível</p>
        <h2 id="level-title" className="mt-1 text-[22px] font-semibold tracking-tight text-white">
          Qual é o seu nível de inglês?
        </h2>
        <p className="mt-1 text-[14px] text-slate-400">
          O professor lê uma conversa, estima o seu nível e aponta o que melhorar, com trechos da sua própria fala.
        </p>
      </div>

      <Card className="flex flex-wrap items-end gap-4 !p-6">
        <label className="min-w-[240px] flex-1">
          <span className="label">Conversa</span>
          <select
            className="field"
            value={chosen}
            onChange={(e) => setChosen(e.target.value ? Number(e.target.value) : "")}
            disabled={busy !== null || sessions.length === 0}
          >
            {sessions.length === 0 && <option value="">Nenhuma conversa com falas ainda</option>}
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title || "Conversa"} · {formatDateTime(s.started_at)} · {s.message_count} mensagens
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn-primary h-11 px-6"
          onClick={() => void analyze()}
          disabled={busy !== null || chosen === ""}
        >
          {busy === "analyze" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {busy === "analyze" ? "Analisando…" : "Analisar conversa"}
        </button>
        {busy === "analyze" && (
          <p className="w-full text-[13px] text-slate-400" role="status">
            Isso pode levar alguns minutos, porque o modelo roda no seu computador.
          </p>
        )}
      </Card>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {current && <AnalysisView analysis={current} />}

      {analyses === null && !error && <Spinner label="Carregando análises…" />}
      {analyses && analyses.length > 0 && (
        <div className="mt-6">
          <p className="mb-3 px-1 text-[13px] text-slate-500">Análises anteriores</p>
          <div className="flex flex-col gap-2">
            {analyses.map((a) => (
              <button
                key={a.id}
                type="button"
                onClick={() => void open(a.id)}
                disabled={busy !== null}
                className="card card-interactive flex items-center justify-between gap-4 !p-4 text-left"
              >
                <div className="min-w-0">
                  <p className="truncate text-[14px] text-white">{a.session_title || "Conversa"}</p>
                  <p className="text-[12px] text-slate-500">
                    {formatDateTime(a.created_at)} · {a.student_turns} falas úteis
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone={CONFIDENCE_TONE[a.confidence]}>confiança {a.confidence}</Badge>
                  <span className="text-[17px] font-semibold text-white">{a.level_estimate}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function AnalysisView({ analysis }: { analysis: LevelAnalysis }) {
  return (
    <Card className="mt-6 flex flex-col gap-6 !p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[13px] text-slate-400">Nível estimado</p>
          <p className="text-[40px] font-semibold tracking-tight text-white">{analysis.level_estimate}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={CONFIDENCE_TONE[analysis.confidence]}>confiança {analysis.confidence}</Badge>
          <p className="text-[12px] text-slate-500">{analysis.student_turns} falas úteis analisadas</p>
        </div>
      </div>

      <p className="text-[15px] leading-relaxed text-slate-200">{analysis.level_reasoning_pt}</p>
      {analysis.level_vs_declared_pt && <p className="text-[14px] text-slate-400">{analysis.level_vs_declared_pt}</p>}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {(Object.keys(CRITERIA_LABELS) as (keyof LevelAnalysis["criteria"])[]).map((key) => (
          <div key={key} className="rounded-2xl border border-line bg-white/[0.04] px-3 py-3 text-center">
            <p className="text-[12px] text-slate-500">{CRITERIA_LABELS[key]}</p>
            <p className="mt-1 text-[16px] font-semibold text-white">{analysis.criteria[key]}</p>
          </div>
        ))}
      </div>

      {analysis.strengths.length > 0 && (
        <div>
          <p className="eyebrow mb-3">Pontos fortes</p>
          <ul className="flex flex-col gap-3">
            {analysis.strengths.map((s, i) => (
              <li key={i} className="text-[14px] text-slate-300">
                {s.text_pt}
                <Quote text={s.evidence.quote} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.improvement_points.length > 0 && (
        <div>
          <p className="eyebrow mb-3">O que melhorar</p>
          <div className="flex flex-col gap-4">
            {analysis.improvement_points.map((p, i) => (
              <div key={i} className="rounded-2xl border border-line bg-white/[0.03] p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Badge tone={p.priority === "alta" ? "bad" : p.priority === "média" ? "warn" : "neutral"}>
                    prioridade {p.priority}
                  </Badge>
                  <span className="text-[12px] text-slate-500">{p.area}</span>
                </div>
                <p className="text-[15px] text-white">{p.issue_pt}</p>
                <Quote text={p.evidence.quote} />
                <p className="mt-3 text-[14px] text-slate-300">{p.suggestion_pt}</p>
                {p.better_example && <p className="mt-2 text-[14px] text-emerald-200">Melhor: “{p.better_example}”</p>}
                {p.practice_pt && <p className="mt-2 text-[13px] text-slate-400">Prática: {p.practice_pt}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.transcription_doubts.length > 0 && (
        <InfoBanner>
          Algumas palavras podem ter sido reconhecidas de forma errada pela voz, então não entraram na avaliação (
          {analysis.transcription_doubts.length}).
        </InfoBanner>
      )}

      <p className="border-t border-line pt-5 text-[15px] text-white">
        <span className="text-slate-400">Próximo passo: </span>
        {analysis.next_step_pt}
      </p>
    </Card>
  );
}

function Quote({ text }: { text: string }) {
  return <p className="mt-1.5 border-l-2 border-line pl-3 text-[13px] italic text-slate-400">“{text}”</p>;
}
