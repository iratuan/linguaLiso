import type * as T from "./types";

// Cliente HTTP do backend. Todos os erros viram ApiError com código estável,
// para a interface decidir a mensagem exibida sem depender do texto do servidor.

export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) {
    return "Não consegui me conectar ao backend. Verifique se ele está em execução.";
  }
  if (error instanceof Error) return error.message;
  return "Erro inesperado.";
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Falha na requisição (HTTP ${response.status}).`;
  let code = "http_error";
  try {
    const body = (await response.json()) as { detail?: unknown; code?: string };
    if (typeof body.detail === "string") detail = body.detail;
    else if (Array.isArray(body.detail)) detail = "Dados inválidos. Verifique os campos e tente de novo.";
    if (body.code) code = body.code;
  } catch {
    // corpo que não é JSON: mantém a mensagem genérica
  }
  return new ApiError(detail, response.status, code);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = init.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init.headers ?? {}) },
  });
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const put = (body: unknown): RequestInit => ({ method: "PUT", body: JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),
  diagnostics: () => request<T.Diagnostics>("/diagnostics"),

  getSettings: () => request<T.Settings>("/settings"),
  updateSettings: (values: Partial<T.Settings>) => request<T.Settings>("/settings", put(values)),

  getProfile: () => request<T.Profile | null>("/profile"),
  saveProfile: (profile: T.Profile) => request<T.Profile>("/profile", put(profile)),

  listSessions: () => request<T.Session[]>("/sessions"),
  createSession: (mode: T.Mode, scenario?: string) =>
    request<T.Session>("/sessions", json({ mode, scenario: scenario ?? null })),
  getSession: (id: number) => request<T.Transcript>(`/sessions/${id}`),
  endSession: (id: number) => request<T.Session>(`/sessions/${id}/end`, { method: "POST" }),
  studyMaterial: (id: number) => request<T.StudyMaterial>(`/sessions/${id}/study-material`, { method: "POST" }),
  deleteSession: (id: number) => request<void>(`/sessions/${id}`, { method: "DELETE" }),
  analyzeSession: (id: number) => request<T.LevelAnalysis>(`/sessions/${id}/analysis`, { method: "POST" }),
  listAnalyses: () => request<{ analyses: T.AnalysisSummary[] }>("/analyses"),
  getAnalysis: (id: number) => request<T.LevelAnalysis>(`/analyses/${id}`),
  sendMessage: (sessionId: number, content: string, inputSource: "text" | "voice") =>
    request<T.TurnResult>(`/sessions/${sessionId}/messages`, json({ content, input_source: inputSource })),

  speechStatus: () => request<T.SpeechStatus>("/speech/status"),
  transcribe: async (blob: Blob): Promise<{ text: string; empty: boolean; duration_s: number }> => {
    const form = new FormData();
    form.append("audio", blob, "recording.webm");
    return request("/speech/transcribe", { method: "POST", body: form });
  },
  synthesize: async (text: string, rate?: number, volume?: number): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/speech/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, rate, volume }),
    });
    if (!response.ok) throw await parseError(response);
    return response.blob();
  },

  listVocabulary: (dueOnly = false) =>
    request<{ items: T.VocabularyItem[]; counts: T.VocabularyCounts }>(`/vocabulary?due_only=${dueOnly}`),
  createVocabulary: (term: string, translation_pt: string, example_sentence: string) =>
    request<T.VocabularyItem>("/vocabulary", json({ term, translation_pt, example_sentence })),
  reviewVocabulary: (id: number, rating: "forgot" | "hard" | "good") =>
    request<T.VocabularyItem>(`/vocabulary/${id}/review`, json({ rating })),
  deleteVocabulary: (id: number) => request<void>(`/vocabulary/${id}`, { method: "DELETE" }),

  listLessons: () => request<T.LessonListItem[]>("/lessons"),
  createLesson: (objective: string, exerciseCount: number) =>
    request<T.Lesson>("/lessons", json({ objective, exercise_count: exerciseCount })),
  getLesson: (id: number) => request<T.Lesson>(`/lessons/${id}`),
  answerLesson: (id: number, position: number, answer: string) =>
    request<T.Lesson>(`/lessons/${id}/answers`, json({ position, answer })),
  completeLesson: (id: number) => request<T.Lesson>(`/lessons/${id}/complete`, { method: "POST" }),

  course: () => request<T.CourseOverview>("/course"),
  courseLesson: (id: string) => request<T.CourseLesson>(`/course/lessons/${id}`),
  checkExercise: (exerciseId: string, answer: string | number) =>
    request<T.CheckResult>(`/course/exercises/${exerciseId}/check`, json({ answer })),
  completeCourseLesson: (id: string) => request<T.CompleteResult>(`/course/lessons/${id}/complete`, { method: "POST" }),
  retryCourseLesson: (id: string) => request<T.CourseLesson>(`/course/lessons/${id}/retry`, { method: "POST" }),
  drillPacks: () => request<T.DrillPacks>("/drills"),
  drillPack: (id: string) => request<T.DrillPack>(`/drills/${id}`),
  scoreDrill: (packId: string, sentenceIndex: number, transcript: string) =>
    request<T.DrillScore>("/drills/score", json({ pack_id: packId, sentence_index: sentenceIndex, transcript })),
  courseDrafts: () => request<{ drafts: T.CourseDraft[] }>("/course/drafts"),
  generateCourseDrafts: (level: T.Level, topic: string, count: number) =>
    request<T.DraftGeneration>("/course/drafts", json({ level, topic, count })),
  approveCourseDraft: (id: number) =>
    request<{ lesson_id: string; title: string; level: T.Level }>(`/course/drafts/${id}/approve`, { method: "POST" }),
  discardCourseDraft: (id: number) => request<{ ok: boolean }>(`/course/drafts/${id}`, { method: "DELETE" }),
  courseExerciseAudio: async (exerciseId: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/course/exercises/${exerciseId}/audio`);
    if (!response.ok) throw await parseError(response);
    return response.blob();
  },

  progress: () => request<T.Progress>("/progress"),
  evolution: (days: number) => request<T.Evolution>(`/progress/evolution?days=${days}`),
  recurringErrors: () => request<T.RecurringError[]>("/errors/recurring"),

  exportUrl: () => `${API_BASE}/data/export`,
  deleteData: (confirm: string) => request<{ deleted: boolean }>("/data/delete", json({ confirm })),
};
