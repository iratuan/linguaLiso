import { Printer, X } from "lucide-react";
import { LEVEL_LABELS } from "../lib/format";
import { LANGUAGE_LABELS, type StudyMaterial } from "../lib/types";

const BLANK_RE = /(_{3,}\s*\(\d+\))/g;

/** Frase com lacunas: cada "______ (n)" vira um espaço para preencher com a numeração. */
function Sentence({ text }: { text: string }) {
  const parts = text.split(BLANK_RE);
  return (
    <>
      {parts.map((part, i) => {
        const match = /^_{3,}\s*\((\d+)\)$/.exec(part);
        if (!match) return <span key={i}>{part}</span>;
        return (
          <span key={i} className="mx-1 inline-block min-w-[7rem] border-b border-slate-700 text-center align-baseline text-[12px] text-slate-500">
            ({match[1]})
          </span>
        );
      })}
    </>
  );
}

/**
 * Folha do material de apoio. Na tela aparece como uma folha sobre o fundo escuro;
 * ao imprimir (Ctrl+P ou o botão), só a folha é impressa, graças às regras de @media print.
 */
export function StudyMaterialSheet({ material, onClose }: { material: StudyMaterial; onClose: () => void }) {
  const languageLabel = LANGUAGE_LABELS[material.language];
  const date = new Date().toLocaleDateString("pt-BR");

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Material de apoio"
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-6 backdrop-blur-sm print:static print:block print:overflow-visible print:bg-white print:p-0"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="mb-3 flex w-full max-w-[210mm] items-center justify-between gap-3 print:hidden">
        <p className="text-[14px] font-medium text-white">Material de apoio pronto para imprimir</p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-full bg-[#ffffff] px-4 py-2 text-[13px] font-semibold text-slate-900 transition hover:bg-slate-200"
          >
            <Printer className="h-4 w-4" /> Imprimir
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            title="Fechar"
            className="icon-btn !h-9 !w-9"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <article
        id="study-material-print"
        className="w-full max-w-[210mm] rounded-2xl bg-[#ffffff] px-12 py-10 text-[14px] leading-relaxed text-slate-900 shadow-2xl print:max-w-none print:rounded-none print:px-[15mm] print:py-[12mm] print:shadow-none"
      >
        <header className="border-b border-slate-300 pb-4">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
            {languageLabel} · {LEVEL_LABELS[material.level]} · {date}
          </p>
          <h1 className="mt-1 text-[22px] font-semibold text-slate-900">{material.title}</h1>
          <p className="mt-2 text-slate-700">{material.instructions_pt}</p>
          <p className="mt-3 text-[12px] text-slate-500">Nome: ________________________________</p>
        </header>

        {material.summary_points_pt.length > 0 && (
          <section className="mt-5">
            <h2 className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Explicação da conversa</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-800">
              {material.summary_points_pt.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          </section>
        )}

        {material.word_bank.length > 0 && (
          <section className="mt-5 rounded-lg border border-slate-300 px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Banco de palavras</p>
            <p className="mt-1 text-slate-800">{material.word_bank.join("   ·   ")}</p>
          </section>
        )}

        <section className="mt-6">
          <h2 className="text-[13px] font-semibold text-slate-800">Preencha as lacunas</h2>
          <ol className="mt-3 space-y-4">
            {material.items.map((item, i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 shrink-0 text-right font-semibold text-slate-500">{i + 1}.</span>
                <p>
                  <Sentence text={item.sentence} />
                </p>
              </li>
            ))}
          </ol>
        </section>

        {material.corrections.length > 0 && (
          <section className="mt-8 break-inside-avoid">
            <h2 className="text-[13px] font-semibold text-slate-800">Pontos de correção</h2>
            <ol className="mt-3 space-y-3">
              {material.corrections.map((c, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-6 shrink-0 text-right font-semibold text-slate-500">{i + 1}.</span>
                  <div>
                    <p>
                      <span className="line-through decoration-slate-400">{c.wrong}</span>
                      {" → "}
                      <span className="font-semibold text-slate-900">{c.right}</span>
                    </p>
                    {c.explanation_pt && <p className="mt-0.5 text-[12.5px] text-slate-600">{c.explanation_pt}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}

        {material.exercises.length > 0 && (
          <section className="mt-8">
            <h2 className="text-[13px] font-semibold text-slate-800">Exercícios de fixação</h2>
            <ol className="mt-3 space-y-5">
              {material.exercises.map((ex, i) => (
                <li key={i} className="flex gap-3 break-inside-avoid">
                  <span className="w-6 shrink-0 text-right font-semibold text-slate-500">{i + 1}.</span>
                  <div className="flex-1">
                    {ex.kind === "translate" ? (
                      <>
                        <p>
                          Traduza para {languageLabel.toLowerCase()}: <span className="text-slate-800">{ex.prompt}</span>
                        </p>
                        <div className="mt-4 border-b border-slate-400" />
                      </>
                    ) : (
                      <>
                        <p>{ex.prompt}</p>
                        <ul className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-slate-800">
                          {ex.options.map((option, j) => (
                            <li key={j}>
                              ({String.fromCharCode(97 + j)}) {option}
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}

        {material.tips.length > 0 && (
          <footer className="mt-10 border-t border-slate-300 pt-4">
            <h2 className="text-[13px] font-semibold text-slate-800">{material.footer_title_pt}</h2>
            <ul className="mt-2 space-y-2 text-[12.5px] text-slate-700">
              {material.tips.map((tip, i) => (
                <li key={i}>
                  <span className="line-through decoration-slate-400">{tip.wrong}</span>
                  {" → "}
                  <span className="font-semibold text-slate-900">{tip.right}</span>
                  {tip.tip_pt && <span className="text-slate-600"> · {tip.tip_pt}</span>}
                </li>
              ))}
            </ul>
          </footer>
        )}
      </article>
    </div>
  );
}
