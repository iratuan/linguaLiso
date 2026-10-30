import { useEffect, useState } from "react";
import { Check, Loader2, Sparkles, Trash2 } from "lucide-react";
import { api, describeError } from "../../lib/api";
import type { CourseDraft, LanguageCode, Level } from "../../lib/types";
import { Badge, ErrorBanner, InfoBanner, Segmented } from "../ui";
import { RichText } from "./primitives";

const LEVELS: Level[] = ["A1", "A2", "B1", "B2", "C1"];

const TYPE_LABEL: Record<CourseDraft["exercises"][number]["type"], string> = {
  multiple_choice: "Múltipla escolha",
  fill_blank: "Completar",
  translate: "Traduzir",
  reorder: "Ordenar",
  listen: "Ditado",
  open_reply: "Resposta livre",
};

/**
 * Criação de lições pelo modelo. Nada entra na trilha sem aprovação: cada lição fica como rascunho
 * para você revisar a explicação e os exercícios antes de aprovar.
 */
export function DraftsPanel({
  language,
  defaultLevel,
  onApproved,
}: {
  language: LanguageCode;
  defaultLevel: Level;
  onApproved: () => void;
}) {
  const [level, setLevel] = useState<Level>(defaultLevel);
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState<1 | 2 | 3>(1);
  const [drafts, setDrafts] = useState<CourseDraft[]>([]);
  const [busy, setBusy] = useState<"generate" | number | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .courseDrafts()
      // A API lista os rascunhos de todos os idiomas; aqui mostramos só o da trilha atual.
      .then((data) => setDrafts(data.drafts.filter((d) => d.language === language)))
      .catch((e) => setError(describeError(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carrega uma vez por idioma
  }, [language]);

  useEffect(() => setLevel(defaultLevel), [defaultLevel]);

  const generate = async () => {
    setBusy("generate");
    setError(null);
    setReport(null);
    try {
      const result = await api.generateCourseDrafts(level, topic.trim(), count);
      setDrafts((prev) => [...prev, ...result.drafts]);
      const created = result.drafts.length;
      const failed = result.failed;
      setReport(
        failed === 0
          ? `${created} ${created === 1 ? "lição criada" : "lições criadas"}. Revise antes de aprovar.`
          : `${created} criada(s) e ${failed} descartada(s) por não passarem na validação.`,
      );
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const approve = async (draft: CourseDraft) => {
    setBusy(draft.id);
    setError(null);
    try {
      await api.approveCourseDraft(draft.id);
      setDrafts((prev) => prev.filter((d) => d.id !== draft.id));
      onApproved();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const discard = async (draft: CourseDraft) => {
    setBusy(draft.id);
    setError(null);
    try {
      await api.discardCourseDraft(draft.id);
      setDrafts((prev) => prev.filter((d) => d.id !== draft.id));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="mt-12" aria-labelledby="drafts-title">
      <div className="mb-5 px-1">
        <p className="eyebrow">Criar lições</p>
        <h2 id="drafts-title" className="mt-1 text-[22px] font-semibold tracking-tight text-white">
          Gerar novas lições para a trilha
        </h2>
        <p className="mt-1 text-[14px] text-slate-400">
          O professor cria a lição e ela fica como rascunho. Só entra na trilha depois da sua aprovação.
        </p>
      </div>

      <div className="card flex flex-col gap-5 !p-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <p className="label">Nível</p>
            <Segmented
              label="Nível da nova lição"
              value={level}
              onChange={setLevel}
              options={LEVELS.map((code) => ({ value: code, label: code }))}
              disabled={busy !== null}
            />
          </div>
          <div>
            <p className="label">Quantas</p>
            <Segmented
              label="Quantidade de lições"
              value={String(count) as "1" | "2" | "3"}
              onChange={(v) => setCount(Number(v) as 1 | 2 | 3)}
              options={[
                { value: "1", label: "1" },
                { value: "2", label: "2" },
                { value: "3", label: "3" },
              ]}
              disabled={busy !== null}
            />
          </div>
          <label className="min-w-[220px] flex-1">
            <span className="label">Tema (opcional)</span>
            <input
              className="field"
              value={topic}
              maxLength={120}
              placeholder="Ex.: pedir comida, falar do tempo… (vazio = o professor escolhe)"
              onChange={(e) => setTopic(e.target.value)}
              disabled={busy !== null}
            />
          </label>
          <button
            type="button"
            className="btn-primary h-11 px-6"
            onClick={() => void generate()}
            disabled={busy !== null}
          >
            {busy === "generate" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {busy === "generate" ? "Gerando…" : "Gerar lições"}
          </button>
        </div>
        {busy === "generate" && (
          <p className="text-[13px] text-slate-400" role="status">
            Isso pode levar alguns minutos, porque o modelo roda no seu computador.
          </p>
        )}
        {report && <InfoBanner>{report}</InfoBanner>}
      </div>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {drafts.length > 0 && (
        <div className="mt-6 flex flex-col gap-5">
          {drafts.map((draft) => (
            <article key={draft.id} className="card animate-rise flex flex-col gap-5 !p-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="info">{draft.level}</Badge>
                <Badge tone="warn">rascunho</Badge>
                <span className="text-[12px] text-slate-500">{draft.exercises.length} exercícios</span>
              </div>
              <div>
                <h3 className="text-[19px] font-semibold text-white">{draft.title}</h3>
                <p className="mt-1 text-[14px] text-slate-400">{draft.objective}</p>
              </div>
              <div className="text-[15px] leading-relaxed text-slate-200">
                <RichText source={draft.explanation} />
              </div>
              {draft.key_phrases.length > 0 && (
                <ul className="flex flex-col gap-2 text-[14px]">
                  {draft.key_phrases.map((p) => (
                    <li key={p.en} className="flex flex-wrap gap-2">
                      <span className="font-medium text-white">{p.en}</span>
                      <span className="text-slate-500">— {p.pt}</span>
                    </li>
                  ))}
                </ul>
              )}
              <ol className="flex flex-col gap-2 border-t border-line pt-4 text-[14px]">
                {draft.exercises.map((ex, i) => (
                  <li key={i} className="flex flex-wrap gap-2 text-slate-300">
                    <span className="text-slate-500">{i + 1}.</span>
                    <span className="text-[12px] text-brand-300">{TYPE_LABEL[ex.type]}</span>
                    <span>{ex.prompt}</span>
                  </li>
                ))}
              </ol>
              <div className="flex flex-wrap justify-end gap-3 border-t border-line pt-4">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => void discard(draft)}
                  disabled={busy !== null}
                >
                  <Trash2 className="h-4 w-4" /> Descartar
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => void approve(draft)}
                  disabled={busy !== null}
                >
                  {busy === draft.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  Aprovar e adicionar à trilha
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
