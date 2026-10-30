import { useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Headphones,
  Lightbulb,
  Loader2,
  Mic,
  RotateCcw,
  Square,
  XCircle,
} from "lucide-react";
import type { CheckResult, CourseExercise } from "../../lib/types";
import { describeError } from "../../lib/api";
import { MAX_RECORDING_MS, useRecorder } from "../../hooks/useVoice";
import { VoiceMeter } from "../ui";
import { InlineText } from "./primitives";

interface Props {
  exercise: CourseExercise;
  index: number;
  total: number;
  isLast: boolean;
  onCheck: (answer: string | number) => Promise<CheckResult>;
  onNext: () => void;
  onListen: () => void;
  listening: boolean;
  onError: (message: string) => void;
}

const TYPE_LABEL: Record<CourseExercise["type"], string> = {
  multiple_choice: "Escolha a opção",
  fill_blank: "Complete a lacuna",
  translate: "Traduza",
  reorder: "Monte a frase",
  listen: "Ouça e escreva",
  open_reply: "Responda ao professor",
};

export function ExerciseCard({ exercise, index, total, isLast, onCheck, onNext, onListen, listening, onError }: Props) {
  const [choice, setChoice] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<number[]>([]); // índices das palavras escolhidas (reorder)
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  // Respostas livres podem ser ditas em voz alta: a transcrição preenche o campo para revisão.
  const recorder = useRecorder((transcript) => setText(transcript), onError);

  const answered = exercise.answered;
  const readOnly = answered || result !== null;
  const correctNow = result?.correct ?? (answered ? exercise.correct : null);
  const reorderAnswer = useMemo(() => picked.map((i) => exercise.words?.[i] ?? "").join(" "), [picked, exercise.words]);

  const currentAnswer: string | number | null =
    exercise.type === "multiple_choice" ? choice : exercise.type === "reorder" ? reorderAnswer : text;

  const canCheck = currentAnswer !== null && currentAnswer !== "" && !readOnly && !checking;

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!canCheck || currentAnswer === null) return;
    setChecking(true);
    try {
      setResult(await onCheck(currentAnswer));
    } catch (e) {
      onError(describeError(e));
    } finally {
      setChecking(false);
    }
  };

  const feedbackOk = correctNow === true;
  const showFeedback = result !== null || (answered && exercise.correct !== null);

  return (
    <div className="animate-rise flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <p className="eyebrow">{TYPE_LABEL[exercise.type]}</p>
        <span className="text-[13px] tabular-nums text-slate-500">
          {index + 1} / {total}
        </span>
      </div>

      {exercise.type === "open_reply" && exercise.context && (
        <p className="-mb-2 text-[14px] text-slate-400">
          <span className="font-medium text-slate-300">Situação:</span> {exercise.context}
        </p>
      )}

      <h2 className="text-[26px] font-semibold leading-snug tracking-[-0.02em] text-white">{exercise.prompt}</h2>

      {(exercise.type === "listen" || exercise.type === "open_reply") && (
        <button
          type="button"
          onClick={onListen}
          disabled={listening}
          className="group flex w-fit items-center gap-3 rounded-full bg-white/[0.07] py-3 pl-3 pr-6 text-[15px] font-medium text-white transition hover:bg-white/[0.12] active:scale-[0.97]"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-500 shadow-lg shadow-brand-500/30 transition group-hover:scale-105">
            {listening ? <Loader2 className="h-5 w-5 animate-spin" /> : <Headphones className="h-5 w-5" />}
          </span>
          {exercise.type === "listen" ? "Ouvir novamente" : "Ouvir o professor"}
        </button>
      )}

      {exercise.hint && !readOnly && <p className="text-[14px] text-slate-400">💡 {exercise.hint}</p>}

      {/* Entrada conforme o tipo */}
      {exercise.type === "multiple_choice" && (
        <div className="grid gap-3 sm:grid-cols-2">
          {exercise.options?.map((option, i) => {
            const selected = choice === i;
            const isAnswerOption = result && !result.correct && result.correct_answer === option;
            return (
              <button
                key={option}
                type="button"
                disabled={readOnly}
                onClick={() => setChoice(i)}
                className={`rounded-2xl border px-5 py-4 text-left text-[16px] transition duration-300 active:scale-[0.98] disabled:cursor-default ${
                  isAnswerOption
                    ? "border-ios-green/60 bg-ios-green/15 text-slate-100"
                    : selected
                      ? "border-brand-500 bg-brand-500/15 text-slate-100 shadow-[0_0_0_4px_rgba(10,132,255,0.15)]"
                      : "border-line bg-white/[0.04] text-slate-200 hover:bg-white/[0.08]"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>
      )}

      {(exercise.type === "fill_blank" ||
        exercise.type === "translate" ||
        exercise.type === "listen" ||
        exercise.type === "open_reply") && (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <input
              className="field h-14 text-[18px]"
              value={readOnly ? (exercise.last_answer ?? "") : text}
              onChange={(e) => setText(e.target.value)}
              // Enquanto grava ou reconhece a fala, o campo fica travado: a transcrição preencheria por cima.
              disabled={readOnly || recorder.state !== "idle"}
              placeholder={
                exercise.type === "open_reply"
                  ? "Responda em inglês, escrevendo ou falando…"
                  : exercise.type === "translate"
                    ? "Escreva em inglês…"
                    : "Sua resposta…"
              }
              aria-label="Sua resposta"
              autoFocus
              maxLength={500}
            />
            {exercise.type === "open_reply" && !readOnly && (
              <button
                type="button"
                onClick={recorder.toggle}
                disabled={recorder.state === "transcribing" || recorder.micError !== null}
                aria-pressed={recorder.state === "recording"}
                aria-label={recorder.state === "recording" ? "Parar gravação" : "Responder falando"}
                className={`relative flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-white transition-colors active:scale-95 disabled:opacity-40 ${
                  recorder.state === "recording"
                    ? "bg-ios-red shadow-[0_0_0_4px_rgba(255,69,58,0.25)]"
                    : "bg-white/[0.08] hover:bg-white/[0.14]"
                }`}
              >
                {recorder.state === "transcribing" ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : recorder.state === "recording" ? (
                  <Square className="h-4 w-4 fill-current" />
                ) : (
                  <Mic className="h-5 w-5" />
                )}
              </button>
            )}
          </div>
          {exercise.type === "open_reply" && recorder.state === "recording" && (
            <div className="flex flex-wrap items-center gap-3" role="status">
              <VoiceMeter level={recorder.level} elapsedMs={recorder.elapsedMs} maxMs={MAX_RECORDING_MS} />
              <span className="text-[13px] text-slate-400">Fale agora. Pare de falar ou toque em parar.</span>
            </div>
          )}
          {exercise.type === "open_reply" && recorder.state === "transcribing" && (
            <p className="text-[13px] text-slate-400" role="status">
              Reconhecendo sua fala…
            </p>
          )}
        </form>
      )}

      {exercise.type === "reorder" && (
        <ReorderArea
          words={exercise.words ?? []}
          picked={readOnly ? [] : picked}
          readOnlyAnswer={readOnly ? (exercise.last_answer ?? "") : null}
          onPick={(i) => setPicked((p) => [...p, i])}
          onUnpick={(pos) => setPicked((p) => p.filter((_, idx) => idx !== pos))}
          disabled={readOnly}
        />
      )}

      {/* Ações e feedback */}
      {!showFeedback && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="btn-primary h-12 px-7"
            onClick={() => void submit()}
            disabled={!canCheck || recorder.state !== "idle"}
          >
            {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Verificar
          </button>
          {exercise.type === "reorder" && picked.length > 0 && (
            <button type="button" className="btn-ghost h-12" onClick={() => setPicked([])}>
              <RotateCcw className="h-4 w-4" /> Limpar
            </button>
          )}
        </div>
      )}

      {showFeedback && (
        <div
          role="status"
          aria-live="polite"
          className={`animate-sheet rounded-[22px] border p-5 ${
            feedbackOk ? "border-ios-green/35 bg-ios-green/[0.08]" : "border-ios-red/35 bg-ios-red/[0.08]"
          }`}
        >
          <div className="flex items-start gap-3">
            <span
              className={`animate-pop mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${feedbackOk ? "bg-ios-green/20 text-ios-green" : "bg-ios-red/20 text-ios-red"}`}
            >
              {feedbackOk ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[17px] font-semibold text-white">{feedbackOk ? "Muito bem!" : "Quase lá"}</p>
              {result?.feedback_pt && (
                <p className="mt-1 text-[15px] leading-relaxed text-slate-200">
                  <InlineText text={result.feedback_pt} />
                </p>
              )}
              {result?.used_ai_check && (
                <p className="mt-2 text-[12px] text-slate-500">
                  Avaliado pelo professor (aceita variações equivalentes).
                </p>
              )}
              {!feedbackOk && result?.correct_answer && (
                <p className="mt-3 flex items-start gap-2 rounded-xl bg-white/[0.06] px-3 py-2 text-[15px] text-slate-100">
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                  <span>
                    Resposta esperada: <strong className="font-semibold text-white">{result.correct_answer}</strong>
                  </span>
                </p>
              )}
            </div>
          </div>
          <div className="mt-5 flex justify-end">
            <button type="button" className="btn-primary" onClick={onNext}>
              {isLast ? "Ver resultado" : "Continuar"} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ReorderArea({
  words,
  picked,
  readOnlyAnswer,
  onPick,
  onUnpick,
  disabled,
}: {
  words: string[];
  picked: number[];
  readOnlyAnswer: string | null;
  onPick: (index: number) => void;
  onUnpick: (position: number) => void;
  disabled: boolean;
}) {
  const used = new Set(picked);
  return (
    <div className="flex flex-col gap-5">
      <div className="min-h-[68px] rounded-[20px] border border-dashed border-white/15 bg-white/[0.03] p-3">
        {readOnlyAnswer !== null ? (
          <p className="px-2 py-1 text-[18px] text-white">{readOnlyAnswer}</p>
        ) : picked.length === 0 ? (
          <p className="px-2 py-1 text-[15px] text-slate-500">Toque nas palavras para montar a frase.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {picked.map((wordIndex, pos) => (
              <button
                key={`${wordIndex}-${pos}`}
                type="button"
                disabled={disabled}
                onClick={() => onUnpick(pos)}
                className="animate-pop rounded-xl bg-brand-500 px-3.5 py-2 text-[16px] font-medium text-on-accent shadow-md shadow-brand-500/25 transition active:scale-95"
              >
                {words[wordIndex]}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {words.map((word, i) => (
          <button
            key={`${word}-${i}`}
            type="button"
            disabled={disabled || used.has(i)}
            onClick={() => onPick(i)}
            className="rounded-xl border border-line bg-white/[0.06] px-3.5 py-2 text-[16px] text-slate-100 transition duration-300 hover:bg-white/[0.12] active:scale-95 disabled:opacity-20"
          >
            {word}
          </button>
        ))}
      </div>
    </div>
  );
}
