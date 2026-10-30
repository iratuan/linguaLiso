import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Check, CircleDot, Lock, Mic, Play, Sparkles } from "lucide-react";
import { api, describeError } from "../lib/api";
import type { CourseLessonSummary, CourseLevel, CourseOverview, Level } from "../lib/types";
import { ErrorBanner, PageContainer, PageHeader, Spinner } from "../components/ui";
import { ProgressRing } from "../components/course/primitives";
import { DraftsPanel } from "../components/course/DraftsPanel";

export function CoursePage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<CourseOverview | null>(null);
  const [selected, setSelected] = useState<Level | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reloadOverview = () => {
    api
      .course()
      .then(setOverview)
      .catch((e) => setError(describeError(e)));
  };

  useEffect(() => {
    api
      .course()
      .then((data) => {
        setOverview(data);
        const nextLevel = data.levels.find((lv) => lv.completed < lv.total) ?? data.levels[0];
        setSelected(nextLevel.code);
      })
      .catch((e) => setError(describeError(e)));
  }, []);

  const level = useMemo<CourseLevel | undefined>(
    () => overview?.levels.find((lv) => lv.code === selected),
    [overview, selected],
  );

  const nextLesson = useMemo(() => {
    if (!overview?.next_lesson_id) return null;
    for (const lv of overview.levels) {
      for (const unit of lv.units) {
        const found = unit.lessons.find((l) => l.id === overview.next_lesson_id);
        if (found) return { lesson: found, level: lv.code };
      }
    }
    return null;
  }, [overview]);

  if (!overview && !error) {
    return (
      <div className="p-10">
        <Spinner label="Carregando trilha…" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer wide>
        <PageHeader
          path="/trilhas"
          eyebrow="Trilha de estudo"
          title={overview ? `Trilha de ${overview.language.name.toLowerCase()}` : "Trilha de estudo"}
          subtitle="Lições curtas, exercícios corrigidos na hora e uma progressão de A1 a C1. Cada lição libera a próxima."
        />
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {overview && (
          <>
            <section className="card animate-rise mb-8 flex flex-wrap items-center gap-8 overflow-hidden !p-7">
              <ProgressRing
                percent={overview.progress.percent}
                size={104}
                stroke={9}
                label={
                  <>
                    <span className="text-[22px] font-semibold text-white">{overview.progress.percent}%</span>
                    <span className="text-[11px] text-slate-400">concluído</span>
                  </>
                }
              />
              <div className="min-w-[220px] flex-1">
                <p className="text-[13px] text-slate-400">
                  {overview.progress.completed} de {overview.progress.total} lições concluídas
                </p>
                <p className="mt-1 text-[22px] font-semibold tracking-tight text-white">
                  {nextLesson ? nextLesson.lesson.title : "Trilha concluída. Parabéns!"}
                </p>
                {nextLesson && <p className="mt-1 text-[14px] text-slate-400">{nextLesson.lesson.objective}</p>}
              </div>
              {nextLesson && (
                <button
                  type="button"
                  className="btn-primary h-12 px-6"
                  onClick={() => navigate(`/trilhas/${nextLesson.lesson.id}`)}
                >
                  <Play className="h-4 w-4 fill-current" /> Continuar
                </button>
              )}
            </section>

            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div role="tablist" aria-label="Níveis" className="segmented">
                {overview.levels.map((lv) => (
                  <button
                    key={lv.code}
                    role="tab"
                    aria-selected={selected === lv.code}
                    type="button"
                    onClick={() => setSelected(lv.code)}
                    className="flex items-center gap-2"
                  >
                    {lv.code}
                    {lv.completed === lv.total && <Check className="h-3.5 w-3.5 text-ios-green" />}
                  </button>
                ))}
              </div>
              {level && (
                <p className="text-[13px] text-slate-400">
                  {level.completed} de {level.total} lições neste nível
                </p>
              )}
            </div>

            {level && (
              <>
                <p className="mb-2 px-1 text-[15px] text-slate-300">
                  <span className="font-semibold text-white">{level.title}.</span> {level.goal}
                </p>
                <div className="mt-8 flex flex-col gap-10">
                  {level.units.map((unit, unitIndex) => (
                    <section key={unit.id} className="animate-rise" style={{ animationDelay: `${unitIndex * 70}ms` }}>
                      <div className="mb-4 px-1">
                        <p className="eyebrow">Unidade {unitIndex + 1}</p>
                        <h2 className="mt-1 text-[22px] font-semibold tracking-tight text-white">{unit.title}</h2>
                        <p className="mt-1 text-[14px] text-slate-400">{unit.goal}</p>
                      </div>
                      <div className="flex flex-col gap-3">
                        {unit.lessons.map((lesson, i) => (
                          <LessonRow key={lesson.id} lesson={lesson} delay={unitIndex * 70 + i * 40} />
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </>
            )}

            <div className="card mt-12 flex flex-wrap items-center justify-between gap-4 !p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/[0.08] text-brand-300">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-white">Quer algo sob medida?</p>
                  <p className="text-[14px] text-slate-400">Peça ao professor uma aula sobre qualquer tema.</p>
                </div>
              </div>
              <Link to="/aulas" className="btn-ghost">
                Aula sob medida <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="card mt-6 flex flex-wrap items-center justify-between gap-4 !p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/[0.08] text-brand-300">
                  <Mic className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-white">Treino de repetição</p>
                  <p className="text-[14px] text-slate-400">Repita frases de um contexto até a fala ficar boa.</p>
                </div>
              </div>
              <Link to="/treino" className="btn-ghost">
                Praticar <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <DraftsPanel
              language={overview.language.code}
              defaultLevel={selected ?? "A1"}
              onApproved={reloadOverview}
            />
          </>
        )}
      </PageContainer>
    </div>
  );
}

function LessonRow({ lesson, delay }: { lesson: CourseLessonSummary; delay: number }) {
  const locked = lesson.status === "locked";
  const done = lesson.status === "completed";
  const inProgress = lesson.status === "in_progress";
  const icon = locked ? (
    <Lock className="h-4 w-4" />
  ) : done ? (
    <Check className="h-4 w-4" />
  ) : inProgress ? (
    <CircleDot className="h-4 w-4" />
  ) : (
    <Play className="h-4 w-4 fill-current" />
  );

  const iconTone = locked
    ? "bg-white/[0.05] text-slate-500"
    : done
      ? "bg-ios-green/20 text-ios-green"
      : inProgress
        ? "bg-ios-orange/20 text-ios-orange"
        : "bg-brand-500 text-on-accent shadow-lg shadow-brand-500/30";

  const content = (
    <>
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition ${iconTone}`}>
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[12px] tabular-nums text-slate-500">Lição {lesson.position}</span>
          {done && lesson.score !== null && (
            <span className="rounded-full bg-ios-green/15 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
              {lesson.score}%
            </span>
          )}
          {inProgress && (
            <span className="rounded-full bg-ios-orange/15 px-2 py-0.5 text-[11px] font-medium text-amber-300">
              em andamento
            </span>
          )}
        </div>
        <p className={`mt-0.5 text-[16px] font-medium ${locked ? "text-slate-500" : "text-white"}`}>{lesson.title}</p>
        <p className={`mt-0.5 text-[14px] ${locked ? "text-slate-600" : "text-slate-400"}`}>{lesson.objective}</p>
      </div>
      <span className="hidden text-[13px] text-slate-500 sm:block">{lesson.exercise_count} exercícios</span>
    </>
  );

  if (locked) {
    return (
      <div
        className="card animate-rise flex items-center gap-4 opacity-60 !p-4"
        style={{ animationDelay: `${delay}ms` }}
        aria-disabled="true"
      >
        {content}
      </div>
    );
  }

  return (
    <Link
      to={`/trilhas/${lesson.id}`}
      className="card card-interactive animate-rise flex items-center gap-4 !p-4"
      style={{ animationDelay: `${delay}ms` }}
    >
      {content}
    </Link>
  );
}
