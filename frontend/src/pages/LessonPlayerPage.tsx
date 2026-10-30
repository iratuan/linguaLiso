import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Lock, RotateCcw, Trophy, Volume2 } from "lucide-react";
import { api, ApiError, describeError } from "../lib/api";
import { playWav, type PlaybackHandle } from "../lib/audio";
import type { CheckResult, CompleteResult, CourseLesson } from "../lib/types";
import { ErrorBanner, Spinner } from "../components/ui";
import { ExerciseCard } from "../components/course/ExerciseCard";
import { ProgressRing, RichText } from "../components/course/primitives";

type Step = "intro" | "exercise" | "result";

export function LessonPlayerPage() {
  const { lessonId = "" } = useParams();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState<CourseLesson | null>(null);
  const [loadError, setLoadError] = useState<ApiError | Error | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("intro");
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<CompleteResult | null>(null);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const playing = useRef<PlaybackHandle | null>(null);

  // Recarrega a lição sem mexer no passo atual (ex.: manter a tela de resultado).
  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setLesson(await api.courseLesson(lessonId));
    } catch (e) {
      setLoadError(e instanceof Error ? e : new Error(describeError(e)));
    }
  }, [lessonId]);

  useEffect(() => {
    void load();
    return () => {
      playing.current?.stop();
    };
  }, [load]);

  /** Toca um áudio, interrompendo qualquer reprodução anterior. `speaking` guarda a chave ativa. */
  const play = async (audio: Promise<Blob>, key: string) => {
    playing.current?.stop();
    setSpeaking(key);
    try {
      const handle = playWav(await audio);
      playing.current = handle;
      await handle.finished;
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSpeaking((current) => (current === key ? null : current));
    }
  };

  const speakPhrase = (text: string) => play(api.synthesize(text), `phrase:${text}`);
  /** Ditado: o áudio vem do servidor, sem expor o texto. Resposta livre: o professor fala a própria fala. */
  const playListening = (exercise: { id: string; type: string; prompt: string }) =>
    exercise.type === "open_reply"
      ? play(api.synthesize(exercise.prompt), `listen:${exercise.id}`)
      : play(api.courseExerciseAudio(exercise.id), `listen:${exercise.id}`);

  if (loadError) {
    const locked = loadError instanceof ApiError && loadError.status === 403;
    return (
      <div className="flex flex-1 items-center justify-center p-10">
        <div className="card animate-rise max-w-md text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-white/[0.07] text-slate-300">
            <Lock className="h-6 w-6" />
          </div>
          <h1 className="text-[20px] font-semibold text-white">
            {locked ? "Lição bloqueada" : "Não foi possível abrir a lição"}
          </h1>
          <p className="mt-2 text-[15px] text-slate-400">
            {locked ? "Conclua a lição anterior para liberar esta." : loadError.message}
          </p>
          <Link to="/trilhas" className="btn-primary mt-6">
            Voltar à trilha
          </Link>
        </div>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="p-10">
        <Spinner label="Abrindo lição…" />
      </div>
    );
  }

  const total = lesson.exercises.length;
  const answeredCount = lesson.exercises.filter((e) => e.answered).length;
  const currentExercise = lesson.exercises[index];
  const passedBefore = lesson.status === "completed";

  // Lição retomada: começa do primeiro exercício pendente.
  const startExercises = () => {
    const firstPending = lesson.exercises.findIndex((e) => !e.answered);
    setIndex(firstPending === -1 ? 0 : firstPending);
    setStep("exercise");
  };

  const handleCheck = async (answer: string | number): Promise<CheckResult> => {
    const checked = await api.checkExercise(currentExercise.id, answer);
    setLesson((prev) =>
      prev
        ? {
            ...prev,
            exercises: prev.exercises.map((e) =>
              e.id === currentExercise.id
                ? { ...e, answered: true, correct: checked.correct, last_answer: String(answer) }
                : e,
            ),
          }
        : prev,
    );
    return checked;
  };

  const handleNext = async () => {
    if (index + 1 < total) {
      setIndex(index + 1);
      return;
    }
    // Último exercício: conclui a lição e mostra o resultado.
    try {
      const outcome = await api.completeCourseLesson(lesson.id);
      setResult(outcome);
      setStep("result");
      await load();
    } catch (e) {
      setError(describeError(e));
    }
  };

  const retry = async () => {
    try {
      const fresh = await api.retryCourseLesson(lesson.id);
      setLesson(fresh);
      setResult(null);
      setIndex(0);
      setStep("exercise");
    } catch (e) {
      setError(describeError(e));
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 px-10 pt-7">
        <Link to="/trilhas" className="btn-ghost !px-3 !py-1.5 text-[14px]">
          <ArrowLeft className="h-4 w-4" /> Trilhas
        </Link>
        {step === "exercise" && (
          <div className="flex flex-1 items-center gap-4 px-6">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.08]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500 transition-[width] duration-700 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
                style={{ width: `${(answeredCount / total) * 100}%` }}
              />
            </div>
            <span className="text-[13px] tabular-nums text-slate-400">
              {answeredCount}/{total}
            </span>
          </div>
        )}
        <span className="text-[13px] text-slate-500">Lição {lesson.position}</span>
      </header>

      <div className="flex-1 overflow-y-auto px-10 pb-16 pt-8">
        <div className="mx-auto max-w-3xl">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />

          {step === "intro" && (
            <div className="animate-rise flex flex-col gap-8">
              <div>
                <p className="eyebrow">
                  {lesson.level} · {passedBefore ? "Concluída" : "Nova lição"}
                </p>
                <h1 className="title-large mt-2">{lesson.title}</h1>
                <p className="mt-3 text-[17px] leading-relaxed text-slate-400">{lesson.objective}</p>
              </div>

              <RichText source={lesson.explanation} />

              {lesson.key_phrases.length > 0 && (
                <section className="card !p-6">
                  <h2 className="mb-4 text-[15px] font-semibold text-white">Frases-chave</h2>
                  <ul className="flex flex-col divide-y divide-line">
                    {lesson.key_phrases.map((phrase) => (
                      <li key={phrase.en} className="flex items-center gap-4 py-3">
                        <button
                          type="button"
                          onClick={() => void speakPhrase(phrase.en)}
                          disabled={speaking !== null}
                          aria-label={`Ouvir: ${phrase.en}`}
                          className="icon-btn h-9 w-9 shrink-0"
                        >
                          <Volume2 className="h-4 w-4" />
                        </button>
                        <div className="min-w-0">
                          <p className="text-[16px] font-medium text-white">{phrase.en}</p>
                          <p className="text-[14px] text-slate-400">{phrase.pt}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
                <p className="text-[14px] text-slate-500">
                  {total} exercícios · nota mínima de {lesson.pass_score}% para concluir
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  {passedBefore && (
                    // Refazer limpa as respostas e recomeça; a melhor nota já conquistada é mantida.
                    <button type="button" className="btn-ghost h-12 px-5" onClick={() => void retry()}>
                      <RotateCcw className="h-4 w-4" /> Refazer do zero
                    </button>
                  )}
                  <button type="button" className="btn-primary h-12 px-7" onClick={startExercises}>
                    {answeredCount > 0 && !passedBefore
                      ? "Continuar exercícios"
                      : passedBefore
                        ? "Revisar exercícios"
                        : "Começar"}
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === "exercise" && currentExercise && (
            <ExerciseCard
              key={currentExercise.id}
              exercise={currentExercise}
              index={index}
              total={total}
              isLast={index + 1 === total}
              onCheck={handleCheck}
              onNext={() => void handleNext()}
              onListen={() => void playListening(currentExercise)}
              listening={speaking === `listen:${currentExercise.id}`}
              onError={setError}
            />
          )}

          {step === "result" && result && (
            <ResultView
              result={result}
              lessonTitle={lesson.title}
              onRetry={() => void retry()}
              onNext={() => navigate(result.next_lesson_id ? `/trilhas/${result.next_lesson_id}` : "/trilhas")}
              onBack={() => navigate("/trilhas")}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function ResultView({
  result,
  lessonTitle,
  onRetry,
  onNext,
  onBack,
}: {
  result: CompleteResult;
  lessonTitle: string;
  onRetry: () => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const ok = result.passed;
  return (
    <div className="animate-rise card flex flex-col items-center gap-6 !p-10 text-center">
      <ProgressRing
        percent={result.score}
        size={150}
        stroke={11}
        label={
          <>
            <span className="text-[34px] font-semibold tracking-tight text-white">{result.score}%</span>
            <span className="text-[12px] text-slate-400">
              {result.correct} de {result.total}
            </span>
          </>
        }
      />
      <div>
        <p className="eyebrow">{ok ? "Lição concluída" : "Quase lá"}</p>
        <h2 className="mt-2 text-[28px] font-semibold tracking-tight text-white">
          {ok ? "Excelente trabalho!" : "Revise e tente de novo"}
        </h2>
        <p className="mx-auto mt-2 max-w-md text-[15px] leading-relaxed text-slate-400">
          {ok
            ? `Você concluiu “${lessonTitle}”${result.next_lesson_id ? " e liberou a próxima lição." : "."}`
            : `Para concluir, é preciso ${result.pass_score}% de acertos. Refaça a lição para liberar a próxima.`}
        </p>
      </div>
      {ok && <Trophy className="h-6 w-6 text-ios-orange" aria-hidden />}
      <div className="flex flex-wrap justify-center gap-3">
        {ok ? (
          <>
            <button type="button" className="btn-ghost" onClick={onBack}>
              Voltar à trilha
            </button>
            <button type="button" className="btn-ghost" onClick={onRetry}>
              <RotateCcw className="h-4 w-4" /> Refazer lição
            </button>
            {result.next_lesson_id && (
              <button type="button" className="btn-primary" onClick={onNext}>
                Próxima lição <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </>
        ) : (
          <>
            <button type="button" className="btn-ghost" onClick={onBack}>
              Voltar à trilha
            </button>
            <button type="button" className="btn-primary" onClick={onRetry}>
              <RotateCcw className="h-4 w-4" /> Refazer lição
            </button>
          </>
        )}
      </div>
    </div>
  );
}
