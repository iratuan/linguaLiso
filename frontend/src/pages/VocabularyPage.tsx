import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Brain, Check, Languages, Plus, Trash2 } from "lucide-react";
import { api, describeError } from "../lib/api";
import { formatRelativeDue } from "../lib/format";
import type { VocabularyCounts, VocabularyItem } from "../lib/types";
import { Badge, Card, EmptyState, ErrorBanner, PageContainer, PageHeader } from "../components/ui";

const BOX_LABELS = ["Nova", "1 dia", "3 dias", "1 semana", "2 semanas", "1 mês", "2 meses"];
type Rating = "forgot" | "hard" | "good";

export function VocabularyPage() {
  const [items, setItems] = useState<VocabularyItem[]>([]);
  const [due, setDue] = useState<VocabularyItem[]>([]);
  const [counts, setCounts] = useState<VocabularyCounts>({ total: 0, due: 0, mastered: 0 });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [term, setTerm] = useState("");
  const [translation, setTranslation] = useState("");
  const [example, setExample] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [all, dueList] = await Promise.all([api.listVocabulary(false), api.listVocabulary(true)]);
      setItems(all.items);
      setDue(dueList.items);
      setCounts(all.counts);
      setError(null);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const addItem = async (event: FormEvent) => {
    event.preventDefault();
    if (!term.trim()) return;
    setSaving(true);
    try {
      await api.createVocabulary(term.trim(), translation.trim(), example.trim());
      setTerm("");
      setTranslation("");
      setExample("");
      await load();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await api.deleteVocabulary(id);
      await load();
    } catch (e) {
      setError(describeError(e));
    }
  };

  if (reviewing) {
    return (
      <div className="flex-1 overflow-y-auto">
        <PageContainer>
          <ReviewSession
            queue={due}
            onRate={async (id, rating) => {
              await api.reviewVocabulary(id, rating);
            }}
            onClose={() => {
              setReviewing(false);
              void load();
            }}
            onError={setError}
          />
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </PageContainer>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer wide>
        <PageHeader
          path="/vocabulario"
          title="Vocabulário"
          subtitle="Palavras das conversas e das trilhas. Cada palavra volta para revisão em intervalos crescentes."
          actions={
            <button
              type="button"
              className="btn-primary"
              onClick={() => setReviewing(true)}
              disabled={counts.due === 0}
            >
              {counts.due > 0 ? `Revisar agora · ${counts.due}` : "Nada para revisar"}
            </button>
          }
        />
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div className="grid gap-4 sm:grid-cols-3">
          <Stat label="Palavras" value={counts.total} />
          <Stat label="Para hoje" value={counts.due} />
          <Stat label="Dominadas" value={counts.mastered} hint="revisadas em intervalos longos" />
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
          <section className="flex min-w-0 flex-col gap-3">
            <h2 className="px-1 text-[15px] font-semibold text-white">Suas palavras</h2>
            {loading && <p className="px-1 text-[14px] text-slate-400">Carregando…</p>}
            {!loading && items.length === 0 && (
              <Card>
                <EmptyState icon={<Languages className="h-6 w-6" />} title="Nenhuma palavra ainda">
                  As palavras novas aparecem aqui automaticamente quando você conversa com o professor.
                </EmptyState>
              </Card>
            )}
            {items.map((item) => (
              <WordRow key={item.id} item={item} onDelete={() => void remove(item.id)} />
            ))}
          </section>

          <Card className="h-fit">
            <h2 className="mb-4 flex items-center gap-2 text-[15px] font-semibold text-white">
              <Plus className="h-4 w-4 text-brand-300" /> Nova palavra
            </h2>
            <form className="flex flex-col gap-4" onSubmit={addItem}>
              <div>
                <label className="label" htmlFor="vocab-term">
                  Palavra ou expressão
                </label>
                <input
                  id="vocab-term"
                  className="field"
                  value={term}
                  onChange={(e) => setTerm(e.target.value)}
                  maxLength={80}
                  required
                />
              </div>
              <div>
                <label className="label" htmlFor="vocab-translation">
                  Tradução
                </label>
                <input
                  id="vocab-translation"
                  className="field"
                  value={translation}
                  onChange={(e) => setTranslation(e.target.value)}
                  maxLength={200}
                />
              </div>
              <div>
                <label className="label" htmlFor="vocab-example">
                  Exemplo
                </label>
                <input
                  id="vocab-example"
                  className="field"
                  value={example}
                  onChange={(e) => setExample(e.target.value)}
                  maxLength={300}
                />
              </div>
              <button type="submit" className="btn-primary mt-1" disabled={saving || !term.trim()}>
                Salvar palavra
              </button>
            </form>
          </Card>
        </div>
      </PageContainer>
    </div>
  );
}

/** Uma palavra na lista: consulta e remoção, sem ações de revisão (essas ficam na sessão). */
function WordRow({ item, onDelete }: { item: VocabularyItem; onDelete: () => void }) {
  const dueNow = new Date(item.next_review_at).getTime() <= Date.now();
  return (
    <Card className="flex items-center gap-4 !p-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <h3 className="text-[16px] font-semibold text-white">{item.term}</h3>
          {item.translation_pt && <span className="text-[14px] text-slate-400">{item.translation_pt}</span>}
        </div>
        {item.example_sentence && <p className="mt-1 truncate text-[14px] text-slate-500">“{item.example_sentence}”</p>}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <Badge tone={dueNow ? "warn" : item.box >= 4 ? "good" : "neutral"}>
          {dueNow ? "Hoje" : (BOX_LABELS[item.box] ?? "Dominada")}
        </Badge>
        <span className="text-[12px] text-slate-500">{formatRelativeDue(item.next_review_at)}</span>
      </div>
      <button type="button" className="icon-btn h-9 w-9" onClick={onDelete} aria-label={`Remover ${item.term}`}>
        <Trash2 className="h-4 w-4" />
      </button>
    </Card>
  );
}

/**
 * Sessão de revisão: uma palavra por vez. A tradução fica escondida até o aluno tentar lembrar.
 * Atalhos: Espaço revela; 1 = esqueci, 2 = difícil, 3 = lembrei; Esc sai.
 */
function ReviewSession({
  queue,
  onRate,
  onClose,
  onError,
}: {
  queue: VocabularyItem[];
  onRate: (id: number, rating: Rating) => Promise<void>;
  onClose: () => void;
  onError: (message: string) => void;
}) {
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [results, setResults] = useState<Record<Rating, number>>({ forgot: 0, hard: 0, good: 0 });
  const [busy, setBusy] = useState(false);
  const current = queue[index];
  const done = index >= queue.length;

  const rate = useCallback(
    async (rating: Rating) => {
      if (!current || !revealed || busy) return;
      setBusy(true);
      try {
        await onRate(current.id, rating);
        setResults((r) => ({ ...r, [rating]: r[rating] + 1 }));
        setRevealed(false);
        setIndex((i) => i + 1);
      } catch (e) {
        onError(describeError(e));
      } finally {
        setBusy(false);
      }
    },
    [current, revealed, busy, onRate, onError],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (done) return;
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        setRevealed(true);
      }
      if (revealed && event.key === "1") void rate("forgot");
      if (revealed && event.key === "2") void rate("hard");
      if (revealed && event.key === "3") void rate("good");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [done, revealed, rate, onClose]);

  if (queue.length === 0) {
    return (
      <div className="animate-rise flex flex-col items-center gap-6 py-20 text-center">
        <p className="eyebrow">Revisão</p>
        <h1 className="title-large">Nada para revisar agora</h1>
        <p className="max-w-md text-[15px] text-slate-400">
          Volte mais tarde. Cada palavra aparece de novo no momento certo.
        </p>
        <button type="button" className="btn-ghost" onClick={onClose}>
          Voltar ao vocabulário
        </button>
      </div>
    );
  }

  if (done) {
    const total = queue.length;
    return (
      <div className="animate-rise flex flex-col items-center gap-8 py-16 text-center">
        <div className="animate-pop flex h-16 w-16 items-center justify-center rounded-full bg-ios-green/15 text-ios-green">
          <Check className="h-8 w-8" />
        </div>
        <div>
          <p className="eyebrow">Revisão concluída</p>
          <h1 className="title-large mt-2">{total} palavras revisadas</h1>
        </div>
        <div className="flex gap-10 text-[15px]">
          <Result label="Lembrei" value={results.good} tone="text-ios-green" />
          <Result label="Difícil" value={results.hard} tone="text-ios-orange" />
          <Result label="Esqueci" value={results.forgot} tone="text-ios-red" />
        </div>
        <button type="button" className="btn-primary" onClick={onClose}>
          Concluir
        </button>
      </div>
    );
  }

  const progress = (index / queue.length) * 100;
  return (
    <div className="flex flex-col gap-10 py-6">
      <div className="flex items-center justify-between gap-4">
        <button type="button" className="btn-ghost !px-3 !py-1.5 text-[13px]" onClick={onClose}>
          Sair <span className="text-slate-500">esc</span>
        </button>
        <div className="flex flex-1 items-center gap-4 px-4">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.08]">
            <div
              className="h-full rounded-full bg-brand-500 transition-[width] duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-[13px] tabular-nums text-slate-500">
            {index + 1} de {queue.length}
          </span>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setRevealed(true)}
        disabled={revealed}
        className="animate-rise card flex min-h-[320px] flex-col items-center justify-center gap-5 !p-10 text-center transition hover:bg-white/[0.06] disabled:cursor-default disabled:hover:bg-white/[0.035]"
        key={current.id}
      >
        <p className="text-[44px] font-semibold tracking-[-0.03em] text-white">{current.term}</p>
        {revealed ? (
          <div className="animate-rise flex flex-col items-center gap-2">
            <p className="text-[24px] text-brand-200">{current.translation_pt || "—"}</p>
            {current.example_sentence && (
              <p className="max-w-md text-[15px] text-slate-400">“{current.example_sentence}”</p>
            )}
          </div>
        ) : (
          <p className="flex items-center gap-2 text-[14px] text-slate-500">
            <Brain className="h-4 w-4" /> Tente lembrar o significado e toque para ver
          </p>
        )}
      </button>

      <div className="grid grid-cols-3 gap-3" aria-disabled={!revealed}>
        <RatingButton
          label="Esqueci"
          hint="1"
          tone="danger"
          disabled={!revealed || busy}
          onClick={() => void rate("forgot")}
        />
        <RatingButton
          label="Difícil"
          hint="2"
          tone="warn"
          disabled={!revealed || busy}
          onClick={() => void rate("hard")}
        />
        <RatingButton
          label="Lembrei"
          hint="3"
          tone="good"
          disabled={!revealed || busy}
          onClick={() => void rate("good")}
        />
      </div>
    </div>
  );
}

const TONE: Record<"danger" | "warn" | "good", string> = {
  danger: "text-ios-red",
  warn: "text-ios-orange",
  good: "text-ios-green",
};

function RatingButton({
  label,
  hint,
  tone,
  disabled,
  onClick,
}: {
  label: string;
  hint: string;
  tone: "danger" | "warn" | "good";
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex flex-col items-center gap-1 rounded-[18px] border border-line bg-white/[0.05] py-4 text-[15px] font-medium transition duration-200 hover:bg-white/[0.1] active:scale-[0.97] disabled:opacity-30 ${TONE[tone]}`}
    >
      {label}
      <span className="text-[11px] font-normal text-slate-500">{hint}</span>
    </button>
  );
}

function Result({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`text-[28px] font-semibold tabular-nums ${tone}`}>{value}</span>
      <span className="text-slate-400">{label}</span>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <Card>
      <p className="text-[12px] font-medium uppercase tracking-[0.06em] text-slate-500">{label}</p>
      <p className="mt-2 text-[30px] font-semibold tracking-tight text-white">{value}</p>
      {hint && <p className="mt-1 text-[12px] text-slate-500">{hint}</p>}
    </Card>
  );
}
