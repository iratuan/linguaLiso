import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, GraduationCap, Loader2, Send, XCircle } from "lucide-react";
import { api, describeError } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { Lesson, LessonListItem } from "../lib/types";
import { Badge, Card, EmptyState, ErrorBanner, PageContainer, PageHeader, Spinner } from "../components/ui";

// Temas sugeridos em português: o professor gera a aula com o mesmo idioma da interface.
const TOPICS = [
  "Presente simples na rotina diária",
  "Passado simples: contar o que aconteceu ontem",
  "Artigos: a, an e the",
  "Preposições de tempo: in, on e at",
  "Comparativos e superlativos",
  "Pedir comida e bebida num restaurante",
];

export function LessonsPage() {
  const [lessons, setLessons] = useState<LessonListItem[]>([]);
  const [current, setCurrent] = useState<Lesson | null>(null);
  const [objective, setObjective] = useState("");
  const [exerciseCount, setExerciseCount] = useState(3);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});

  const loadList = useCallback(async () => {
    try {
      setLessons(await api.listLessons());
    } catch (e) {
      setError(describeError(e));
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (objective.trim().length < 3) return;
    setBusy("creating");
    setError(null);
    try {
      const lesson = await api.createLesson(objective.trim(), exerciseCount);
      setCurrent(lesson);
      setAnswers({});
      setObjective("");
      await loadList();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const open = async (id: number) => {
    setError(null);
    try {
      const lesson = await api.getLesson(id);
      setCurrent(lesson);
      setAnswers({});
    } catch (e) {
      setError(describeError(e));
    }
  };

  const answer = async (position: number) => {
    if (!current) return;
    const text = answers[position]?.trim();
    if (!text) return;
    setBusy(`answer-${position}`);
    setError(null);
    try {
      setCurrent(await api.answerLesson(current.id, position, text));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const complete = async () => {
    if (!current) return;
    setBusy("complete");
    try {
      setCurrent(await api.completeLesson(current.id));
      await loadList();
    } catch (e) {
      setError(describeError(e));
    } finally {
      setBusy(null);
    }
  };

  const answeredCount = current?.exercises.filter((e) => e.answered_at).length ?? 0;

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer wide>
        <PageHeader
          path="/aulas"
          title="Aula sob medida"
          subtitle="Peça ao professor uma aula sobre qualquer tema. Ela é feita no seu nível e os exercícios são corrigidos na hora."
        />
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div className="mt-4 grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="flex flex-col gap-4">
            <Card>
              <h2 className="mb-3 font-semibold text-white">Nova aula</h2>
              <form className="flex flex-col gap-3" onSubmit={create}>
                <div>
                  <label className="label" htmlFor="lesson-objective">
                    Tema
                  </label>
                  <input
                    id="lesson-objective"
                    className="field"
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    placeholder="Ex.: pedir comida em um restaurante"
                    maxLength={300}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {TOPICS.map((topic) => (
                    <button
                      key={topic}
                      type="button"
                      className="rounded-full border border-line bg-white/[0.05] px-3 py-1 text-[12px] text-slate-300 transition hover:bg-white/[0.1] hover:text-white"
                      onClick={() => setObjective(topic)}
                    >
                      {topic.split(":")[0]}
                    </button>
                  ))}
                </div>
                <div>
                  <label className="label" htmlFor="lesson-count">
                    Exercícios
                  </label>
                  <select
                    id="lesson-count"
                    className="field"
                    value={exerciseCount}
                    onChange={(e) => setExerciseCount(Number(e.target.value))}
                  >
                    {[2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n} exercícios
                      </option>
                    ))}
                  </select>
                </div>
                <button type="submit" className="btn-primary" disabled={busy !== null || objective.trim().length < 3}>
                  {busy === "creating" ? <Spinner label="Criando aula…" /> : "Criar aula"}
                </button>
                <p className="text-xs text-slate-500">A geração usa o modelo local e pode levar alguns segundos.</p>
              </form>
            </Card>

            <Card>
              <h2 className="mb-3 font-semibold text-white">Histórico</h2>
              {lessons.length === 0 && <p className="text-sm text-slate-400">Nenhuma aula ainda.</p>}
              <ul className="flex flex-col gap-1">
                {lessons.map((lesson) => (
                  <li key={lesson.id}>
                    <button
                      type="button"
                      onClick={() => void open(lesson.id)}
                      className={`w-full rounded-xl px-3 py-2 text-left text-sm transition hover:bg-surface-2 ${current?.id === lesson.id ? "bg-surface-2 text-white" : "text-slate-300"}`}
                    >
                      <span className="block truncate font-medium">{lesson.title}</span>
                      <span className="flex items-center gap-2 text-xs text-slate-500">
                        {formatDateTime(lesson.created_at)}
                        {lesson.status === "completed" && <Badge tone="good">concluída</Badge>}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <div className="min-w-0">
            {!current && (
              <Card>
                <EmptyState icon={<GraduationCap className="h-6 w-6" />} title="Escolha um tema">
                  Crie uma aula ou abra uma do histórico para continuar.
                </EmptyState>
              </Card>
            )}

            {current && (
              <div className="flex flex-col gap-5">
                <Card>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-semibold text-white">{current.title}</h2>
                    {current.status === "completed" ? (
                      <Badge tone="good">Concluída</Badge>
                    ) : (
                      <Badge tone="info">Em andamento</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{current.objective}</p>
                  {current.content_md && (
                    <div className="mt-4 whitespace-pre-wrap rounded-xl bg-surface-2 p-4 text-sm leading-relaxed text-slate-200">
                      {current.content_md}
                    </div>
                  )}
                </Card>

                {current.exercises.map((exercise) => {
                  const answered = exercise.answered_at !== null;
                  return (
                    <Card key={exercise.id}>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Exercício {exercise.position}</p>
                      <p className="mt-1 font-medium text-slate-100">{exercise.prompt}</p>

                      {!answered && current.status === "open" && (
                        <form
                          className="mt-3 flex gap-2"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void answer(exercise.position);
                          }}
                        >
                          <input
                            className="field"
                            aria-label={`Resposta do exercício ${exercise.position}`}
                            value={answers[exercise.position] ?? ""}
                            onChange={(e) => setAnswers((prev) => ({ ...prev, [exercise.position]: e.target.value }))}
                            maxLength={500}
                          />
                          <button
                            type="submit"
                            className="btn-primary"
                            disabled={busy !== null || !answers[exercise.position]?.trim()}
                          >
                            {busy === `answer-${exercise.position}` ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Send className="h-4 w-4" />
                            )}
                            Enviar
                          </button>
                        </form>
                      )}

                      {answered && (
                        <div className="mt-3 rounded-xl bg-surface-2 p-3 text-sm">
                          <p className="flex items-center gap-2 text-slate-300">
                            {exercise.is_correct ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                            ) : (
                              <XCircle className="h-4 w-4 text-rose-400" />
                            )}
                            Sua resposta: <span className="text-white">{exercise.user_answer}</span>
                          </p>
                          {exercise.feedback && <p className="mt-2 text-slate-400">{exercise.feedback}</p>}
                        </div>
                      )}
                    </Card>
                  );
                })}

                {current.status === "open" && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-400">
                      {answeredCount} de {current.exercises.length} respondidos
                    </p>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => void complete()}
                      disabled={busy !== null || answeredCount === 0}
                    >
                      Concluir aula
                    </button>
                  </div>
                )}
                {current.summary && <p className="text-sm text-emerald-300">{current.summary}</p>}
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </div>
  );
}
