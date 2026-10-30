import type { ReactNode } from "react";
import { BookMarked, Lightbulb, Volume2, Square } from "lucide-react";
import type { CorrectionData, Message, NewVocabulary, TeacherPersona } from "../lib/types";
import { CATEGORY_LABELS } from "../lib/format";
import { Badge } from "./ui";
import { TeacherAvatar } from "./TeacherAvatar";

export function MessageBubble({
  message,
  onSpeak,
  speaking,
  persona,
  children,
}: {
  message: Message;
  onSpeak?: (text: string) => void;
  speaking?: boolean;
  /** Com a personalidade do professor, a fala dele ganha o avatar ao lado. */
  persona?: TeacherPersona;
  children?: ReactNode;
}) {
  const isUser = message.role === "user";
  const content = (
    <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[78%] rounded-[20px] px-4 py-2.5 text-[16px] leading-relaxed ${
          isUser
            ? "rounded-br-lg bg-gradient-to-b from-[#2b8cff] to-brand-600 text-on-accent shadow-md shadow-brand-600/25"
            : "rounded-bl-lg border border-line bg-white/[0.07] text-slate-100 backdrop-blur-xl"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <div className="mt-1.5 flex items-center gap-2 text-[11px] opacity-70">
          {isUser && message.input_source === "voice" && <span>🎙 voz</span>}
          {!isUser && onSpeak && (
            <button
              type="button"
              onClick={() => onSpeak(message.content)}
              disabled={speaking}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-white/10 disabled:opacity-40"
              aria-label="Ouvir esta resposta"
            >
              <Volume2 className="h-3.5 w-3.5" /> ouvir
            </button>
          )}
        </div>
      </div>
      {children}
    </div>
  );
  if (isUser || !persona) return <div className="animate-rise">{content}</div>;
  return (
    <div className="animate-rise flex items-end gap-2.5">
      <TeacherAvatar persona={persona} size={34} />
      <div className="min-w-0">{content}</div>
    </div>
  );
}

export function CorrectionCard({
  correction,
  onRepeat,
  repeating,
}: {
  correction: CorrectionData;
  onRepeat?: (text: string) => void;
  repeating?: boolean;
}) {
  const tone = correction.severity === "major" ? "bad" : correction.severity === "moderate" ? "info" : "neutral";
  return (
    <div className="max-w-[78%] rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Lightbulb className="h-4 w-4 text-amber-300" />
        <span className="font-medium text-amber-200">Correção</span>
        <Badge tone={tone}>{CATEGORY_LABELS[correction.error_category] ?? correction.error_category}</Badge>
      </div>
      <p className="text-slate-400 line-through decoration-rose-400/70">{correction.original_text}</p>
      <p className="mt-1 font-medium text-emerald-300">{correction.corrected_text}</p>
      {correction.explanation_pt && <p className="mt-2 text-slate-300">{correction.explanation_pt}</p>}
      {correction.example_sentence && (
        <p className="mt-2 text-slate-400">
          <span className="text-slate-500">Exemplo:</span> {correction.example_sentence}
        </p>
      )}
      {correction.practice_prompt && (
        <p className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-slate-300">
          <span className="font-medium text-brand-300">Pratique:</span> {correction.practice_prompt}
        </p>
      )}
      {onRepeat && (
        <button
          type="button"
          onClick={() => onRepeat(correction.corrected_text)}
          disabled={repeating}
          className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-amber-200 hover:text-white disabled:opacity-40"
        >
          {repeating ? <Square className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          Repetir frase corrigida
        </button>
      )}
    </div>
  );
}

export function NewVocabularyChips({ items }: { items: NewVocabulary[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex max-w-[78%] flex-wrap items-center gap-2">
      <BookMarked className="h-4 w-4 text-brand-300" />
      {items.map((item) => (
        <span
          key={item.term}
          title={[item.translation_pt, item.example_sentence].filter(Boolean).join(" · ")}
          className="rounded-full border border-brand-500/30 bg-brand-500/10 px-3 py-1 text-xs text-brand-200"
        >
          {item.term}
          {item.translation_pt && <span className="text-brand-300/70"> · {item.translation_pt}</span>}
        </span>
      ))}
      <span className="text-[11px] text-slate-500">adicionado ao vocabulário</span>
    </div>
  );
}

export function TypingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400" role="status" aria-live="polite">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" />
      </span>
      {label}
    </div>
  );
}
