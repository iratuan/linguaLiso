import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, Check, Headphones, Mic, RotateCcw, Square, SkipForward } from "lucide-react";
import { api, describeError } from "../lib/api";
import type { DrillPack, DrillPackSummary, DrillScore, Settings } from "../lib/types";
import { MAX_RECORDING_MS, useRecorder, usePlayback } from "../hooks/useVoice";
import {
  Badge,
  EmptyState,
  ErrorBanner,
  InfoBanner,
  PageContainer,
  PageHeader,
  Spinner,
  VoiceMeter,
} from "../components/ui";

/** Tentativas por frase antes de mostrar a resposta e seguir em frente. */
const MAX_ATTEMPTS = 3;

type Outcome = "passed" | "missed" | "skipped";

export function DrillsPage() {
  const { packId } = useParams();
  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer>{packId ? <DrillPlayer packId={packId} /> : <DrillList />}</PageContainer>
    </div>
  );
}

function DrillList() {
  const [packs, setPacks] = useState<DrillPackSummary[] | null>(null);
  const [language, setLanguage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .drillPacks()
      .then((data) => {
        setPacks(data.packs);
        setLanguage(data.language);
      })
      .catch((e) => setError(describeError(e)));
  }, []);

  return (
    <>
      <PageHeader
        path="/treino"
        eyebrow="Treino de repetição"
        title="Repita e fixe"
        subtitle="Escolha um contexto. O professor fala uma frase, você repete, e só avança quando a fala for reconhecida com boa precisão."
      />
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {!packs && !error && <Spinner label="Carregando contextos…" />}
      {packs && packs.length === 0 && (
        <EmptyState icon={<Mic className="h-6 w-6" />} title="Nenhum contexto neste idioma ainda">
          Os contextos de treino para este idioma ainda não foram criados.
        </EmptyState>
      )}
      {packs && packs.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {packs.map((pack) => (
            <Link
              key={pack.id}
              to={`/treino/${pack.id}`}
              className="card card-interactive animate-rise flex flex-col gap-4 !p-6"
            >
              <div className="flex items-center justify-between gap-3">
                <Badge tone="info">{pack.level}</Badge>
                <span className="text-[12px] text-slate-500">{pack.sentence_count} frases</span>
              </div>
              <div>
                <p className="text-[18px] font-semibold text-white">{pack.title}</p>
                <p className="mt-1 text-[14px] leading-relaxed text-slate-400">{pack.context}</p>
              </div>
              <span className="mt-auto inline-flex items-center gap-2 text-[14px] font-medium text-brand-300">
                Começar <ArrowRight className="h-4 w-4" />
              </span>
            </Link>
          ))}
        </div>
      )}
      {language && (
        <p className="mt-6 text-[13px] text-slate-500">Idioma: {language === "fr" ? "francês" : "inglês"}</p>
      )}
    </>
  );
}

function DrillPlayer({ packId }: { packId: string }) {
  const navigate = useNavigate();
  const [pack, setPack] = useState<DrillPack | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [index, setIndex] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [score, setScore] = useState<DrillScore | null>(null);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.drillPack(packId), api.getSettings()])
      .then(([p, s]) => {
        setPack(p);
        setSettings(s);
      })
      .catch((e) => setError(describeError(e)));
  }, [packId]);

  const sentence = pack?.sentences[index];
  const finished = pack !== null && outcomes.length >= pack.sentences.length;
  const {
    speak,
    state: playing,
    stop: stopVoice,
  } = usePlayback({ rate: settings?.speech_rate ?? 1, volume: settings?.speech_volume ?? 1 }, setError);

  // Ao transcrever, a fala é pontuada contra a frase atual no servidor.
  const onTranscript = async (transcript: string) => {
    if (!pack || !sentence) return;
    setChecking(true);
    try {
      const result = await api.scoreDrill(pack.id, index, transcript);
      setScore(result);
      setAttempts((n) => n + 1);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setChecking(false);
    }
  };

  const recorder = useRecorder(onTranscript, setError);

  // O resultado da frase só entra no resumo quando o aluno avança.
  const nextSentence = (outcome: Outcome) => {
    setOutcomes((prev) => [...prev, outcome]);
    setScore(null);
    setAttempts(0);
    stopVoice();
    setIndex((i) => i + 1);
  };

  // Quando a frase passou ou as tentativas acabaram, a frase é encerrada pelo botão "Próxima".
  const exhausted = score !== null && !score.passed && attempts >= MAX_ATTEMPTS;
  const canAdvance = score?.passed === true || exhausted;

  const restart = () => {
    setIndex(0);
    setAttempts(0);
    setScore(null);
    setOutcomes([]);
  };

  const summary = useMemo(() => {
    const passed = outcomes.filter((o) => o === "passed").length;
    return { passed, total: pack?.sentences.length ?? 0 };
  }, [outcomes, pack]);

  if (error && !pack) {
    return (
      <>
        <ErrorBanner message={error} />
        <Link to="/treino" className="btn-ghost">
          Voltar aos contextos
        </Link>
      </>
    );
  }
  if (!pack || !settings) return <Spinner label="Carregando treino…" />;

  return (
    <>
      <PageHeader
        path={`/treino/${pack.id}`}
        eyebrow={`${pack.level} · treino de repetição`}
        title={pack.title}
        subtitle={pack.context}
        actions={
          <button type="button" className="btn-ghost" onClick={() => navigate("/treino")}>
            Outros contextos
          </button>
        }
      />
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {finished ? (
        <section className="card animate-rise flex flex-col items-center gap-5 !p-10 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-ios-green/15 text-ios-green">
            <Check className="h-7 w-7" />
          </div>
          <h2 className="text-[22px] font-semibold text-white">
            {summary.passed} de {summary.total} frases repetidas com boa precisão
          </h2>
          <p className="max-w-md text-[14px] text-slate-400">
            Repetir em voz alta várias vezes é o que fixa a fala. Quer praticar de novo?
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <button type="button" className="btn-ghost" onClick={() => navigate("/treino")}>
              Outros contextos
            </button>
            <button type="button" className="btn-primary" onClick={restart}>
              <RotateCcw className="h-4 w-4" /> Repetir o contexto
            </button>
          </div>
        </section>
      ) : (
        sentence && (
          <section className="card animate-rise flex flex-col gap-6 !p-7">
            <div className="flex items-center justify-between gap-4">
              <p className="text-[13px] tabular-nums text-slate-400">
                Frase {index + 1} de {pack.sentences.length}
              </p>
              <ProgressDots total={pack.sentences.length} outcomes={outcomes} current={index} />
            </div>

            <div>
              <p className="text-[24px] font-semibold leading-snug tracking-tight text-white">{sentence.text}</p>
              <p className="mt-2 text-[14px] text-slate-500">{sentence.pt}</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn-ghost"
                onClick={() => void speak(sentence.text)}
                disabled={playing !== "idle" || recorder.state !== "idle"}
              >
                <Headphones className="h-4 w-4" /> {playing === "idle" ? "Ouvir o professor" : "Reproduzindo…"}
              </button>
              <MicButton recorder={recorder} />
              {recorder.state === "recording" && (
                <VoiceMeter level={recorder.level} elapsedMs={recorder.elapsedMs} maxMs={MAX_RECORDING_MS} />
              )}
              {recorder.state === "transcribing" || checking ? (
                <span className="text-[13px] text-slate-400" role="status">
                  Conferindo sua fala…
                </span>
              ) : null}
            </div>

            {score && <Feedback score={score} attempt={attempts} maxAttempts={MAX_ATTEMPTS} exhausted={exhausted} />}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
              <button
                type="button"
                className="btn-ghost"
                onClick={() => nextSentence("skipped")}
                disabled={recorder.state !== "idle" || checking}
              >
                <SkipForward className="h-4 w-4" /> Pular frase
              </button>
              {canAdvance ? (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => nextSentence(score?.passed ? "passed" : "missed")}
                >
                  {index + 1 === pack.sentences.length ? "Concluir" : "Próxima frase"}{" "}
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <span className="text-[13px] text-slate-500">
                  {score ? "Tente de novo pelo microfone." : "Toque no microfone e repita a frase."}
                </span>
              )}
            </div>
          </section>
        )
      )}

      <p className="mt-6 text-[13px] text-slate-500">
        A conferência compara o que foi reconhecido com a frase. Ela não avalia o seu sotaque.
      </p>
    </>
  );
}

function MicButton({ recorder }: { recorder: ReturnType<typeof useRecorder> }) {
  const recording = recorder.state === "recording";
  const busy = recorder.state === "transcribing";
  return (
    <button
      type="button"
      onClick={recorder.toggle}
      disabled={busy || recorder.micError !== null}
      aria-pressed={recording}
      aria-label={recording ? "Parar gravação" : "Repetir a frase"}
      className={`inline-flex h-11 items-center gap-2 rounded-full px-5 text-[15px] font-medium text-white transition-colors active:scale-95 disabled:opacity-40 ${
        recording ? "bg-ios-red shadow-[0_0_0_4px_rgba(255,69,58,0.25)]" : "bg-brand-500 hover:bg-brand-400"
      }`}
    >
      {recording ? <Square className="h-4 w-4 fill-current" /> : <Mic className="h-4 w-4" />}
      {recording ? "Parar" : "Repetir"}
    </button>
  );
}

function Feedback({
  score,
  attempt,
  maxAttempts,
  exhausted,
}: {
  score: DrillScore;
  attempt: number;
  maxAttempts: number;
  exhausted: boolean;
}) {
  if (score.passed) {
    return (
      <InfoBanner>
        <span className="font-semibold text-white">Muito bem!</span> Sua fala foi reconhecida com {score.score}% de
        precisão.
      </InfoBanner>
    );
  }
  return (
    <div className="animate-rise flex flex-col gap-3 rounded-2xl border border-line bg-white/[0.04] px-5 py-4">
      <p className="text-[14px] text-slate-300">
        Reconhecido com {score.score}% de precisão · tentativa {attempt} de {maxAttempts}
      </p>
      {score.missing.length > 0 && (
        <p className="text-[14px] text-slate-400">
          Faltou: <span className="text-amber-200">{score.missing.join(", ")}</span>
        </p>
      )}
      {score.extra.length > 0 && (
        <p className="text-[14px] text-slate-400">
          Sobrou: <span className="text-rose-200">{score.extra.join(", ")}</span>
        </p>
      )}
      {exhausted && (
        <p className="text-[14px] text-slate-300">
          Sem problema. Ouça a frase de novo e siga em frente. Ela volta a aparecer em outros treinos.
        </p>
      )}
    </div>
  );
}

function ProgressDots({ total, outcomes, current }: { total: number; outcomes: Outcome[]; current: number }) {
  return (
    <div className="flex items-center gap-1.5" aria-hidden>
      {Array.from({ length: total }, (_, i) => {
        const outcome = outcomes[i];
        const tone =
          outcome === "passed"
            ? "bg-ios-green"
            : outcome === "missed" || outcome === "skipped"
              ? "bg-ios-orange"
              : i === current
                ? "bg-brand-400"
                : "bg-white/[0.16]";
        return <span key={i} className={`h-1.5 w-4 rounded-full ${tone}`} />;
      })}
    </div>
  );
}
