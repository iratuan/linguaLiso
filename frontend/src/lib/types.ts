export type Level = "A1" | "A2" | "B1" | "B2" | "C1";

export type Mode = "free" | "guided_lesson" | "grammar" | "vocabulary" | "roleplay" | "error_review" | "listening";

export const MODE_LABELS: Record<Mode, string> = {
  free: "Conversação livre",
  guided_lesson: "Aula guiada",
  grammar: "Gramática",
  vocabulary: "Vocabulário",
  roleplay: "Roleplay",
  error_review: "Revisão de erros",
  listening: "Treino de escuta",
};

export const SCENARIO_LABELS: Record<string, string> = {
  airport: "Aeroporto",
  hotel: "Hotel",
  restaurant: "Restaurante",
  shopping: "Compras",
  travel: "Viagem",
  job_interview: "Entrevista de emprego",
  work_meeting: "Reunião profissional",
  small_talk: "Conversa cotidiana",
  customer_service: "Atendimento ao cliente",
};

export interface Profile {
  display_name: string;
  level: Level;
  english_variant: "american" | "british";
  explanation_language: "pt-BR";
  study_minutes_goal: number;
  level_is_manual?: boolean;
  updated_at?: string;
}

export type LanguageCode = "en" | "fr";

/** Personalidade do professor: tom formal, descontraído ou de falante nativo bem-humorado. */
export type TeacherPersona = "formal" | "descontraido" | "nativo";

export const PERSONA_LABELS: Record<TeacherPersona, string> = {
  formal: "Formal",
  descontraido: "Descontraído",
  nativo: "Nativo bem-humorado",
};

export const PERSONA_DESCRIPTIONS: Record<TeacherPersona, string> = {
  formal: "Cortês e polido, como um professor de universidade. Humor raro e seco.",
  descontraido: "Amigável e leve, como um colega de estudos. Humor frequente.",
  nativo: "Espontâneo, cheio de gírias e um pouco distraído. Muito humor, correção intacta.",
};

export const LANGUAGE_LABELS: Record<LanguageCode, string> = {
  en: "Inglês",
  fr: "Francês",
};

export interface Settings {
  target_language: LanguageCode;
  llm_model: string | null;
  llm_model_default: string;
  llm_model_fallback: string;
  llm_temperature: number;
  llm_num_ctx: number;
  history_limit: number;
  speech_voice: string;
  speech_rate: number;
  speech_volume: number;
  confirm_transcription: boolean;
  response_mode: "audio" | "text";
  teacher_persona: TeacherPersona;
  /** Transparência da interface, em %: 0 opaca, 80 quase transparente. */
  ui_transparency: number;
  /** Tema visual: escuro (padrão) ou papel, estilo Kindle. */
  app_theme: "escuro" | "papel";
}

export interface Session {
  id: number;
  language?: LanguageCode;
  persona?: TeacherPersona;
  mode: Mode;
  scenario: string | null;
  title: string;
  level: Level;
  model: string;
  started_at: string;
  ended_at: string | null;
  message_count?: number;
}

export interface Message {
  id: number;
  session_id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  input_source?: "text" | "voice";
  created_at: string;
}

export interface CorrectionData {
  has_error: boolean;
  original_text: string;
  corrected_text: string;
  explanation_pt: string;
  error_category: "grammar" | "vocabulary" | "context" | "spelling" | "other";
  severity: "minor" | "moderate" | "major";
  example_sentence: string;
  practice_prompt: string;
}

export interface SavedCorrection extends CorrectionData {
  id: number;
}

export interface NewVocabulary {
  term: string;
  translation_pt: string;
  example_sentence: string;
}

export interface TurnResult {
  user_message_id: number;
  assistant_message: Message;
  correction: SavedCorrection | null;
  new_vocabulary: NewVocabulary[];
  structured: boolean;
}

export interface Transcript {
  session: Session;
  messages: Message[];
  corrections: (CorrectionData & { id: number; message_id: number; created_at: string })[];
}

export interface StudyMaterialItem {
  sentence: string;
  answers: string[];
}

export interface StudyMaterialTip {
  wrong: string;
  right: string;
  tip_pt: string;
}

export interface StudyMaterialCorrection {
  wrong: string;
  right: string;
  explanation_pt: string;
}

export interface StudyMaterialExercise {
  kind: "translate" | "multiple_choice";
  prompt: string;
  options: string[];
  answer: string;
}

/**
 * Material de apoio gerado a partir da conversa: explicação, exercício de lacunas,
 * pontos de correção, exercícios de fixação e rodapé de revisão.
 */
export interface StudyMaterial {
  session_id: number;
  language: LanguageCode;
  level: Level;
  title: string;
  instructions_pt: string;
  word_bank: string[];
  items: StudyMaterialItem[];
  summary_points_pt: string[];
  corrections: StudyMaterialCorrection[];
  exercises: StudyMaterialExercise[];
  footer_title_pt: string;
  tips: StudyMaterialTip[];
}

export interface VocabularyItem {
  id: number;
  term: string;
  translation_pt: string;
  example_sentence: string;
  box: number;
  next_review_at: string;
  created_at: string;
}

export interface VocabularyCounts {
  total: number;
  due: number;
  mastered: number;
}

export interface LessonExercise {
  id: number;
  position: number;
  prompt: string;
  expected_answer: string;
  user_answer: string | null;
  is_correct: 0 | 1 | null;
  feedback: string;
  answered_at: string | null;
}

export interface Lesson {
  id: number;
  title: string;
  objective: string;
  content_md: string;
  status: "open" | "completed";
  summary: string;
  created_at: string;
  completed_at: string | null;
  exercises: LessonExercise[];
}

export interface LessonListItem {
  id: number;
  title: string;
  objective: string;
  status: "open" | "completed";
  created_at: string;
  completed_at: string | null;
}

export interface Progress {
  totals: { sessions: number; user_messages: number; corrections: number; lessons_completed: number };
  errors_by_category: { category: string; count: number }[];
  daily_sessions: { day: string; sessions: number }[];
  recent_corrections: {
    original_text: string;
    corrected_text: string;
    error_category: string;
    created_at: string;
  }[];
  vocabulary: VocabularyCounts;
  profile: Profile | null;
}

export interface RecurringError {
  corrected_text: string;
  error_category: string;
  explanation_pt: string;
  practice_prompt: string;
  occurrences: number;
}

export interface Diagnostics {
  backend: { version: string; schema_version: number };
  database: { path: string; exists: boolean };
  data_dir: string;
  disk_free_gb: number;
  llm: {
    url: string;
    reachable: boolean;
    selected_model: string;
    model_installed: boolean;
    installed_models: string[];
    message: string;
  };
  speech: {
    url: string;
    reachable: boolean;
    stt_ready: boolean;
    tts_ready: boolean;
    message: string;
  };
}

export type LessonStatus = "locked" | "available" | "in_progress" | "completed";
export type ExerciseType = "multiple_choice" | "fill_blank" | "translate" | "reorder" | "listen" | "open_reply";

export interface EvolutionDay {
  day: string;
  user_messages: number;
  corrections: number;
  accuracy: number | null;
  avg_words: number | null;
  exercises: number;
  exercise_accuracy: number | null;
  lessons_completed: number;
  vocabulary_added: number;
  cumulative_lessons: number;
  cumulative_vocabulary: number;
}

export interface Evolution {
  range_days: number;
  series: EvolutionDay[];
  lesson_scores: { lesson_id: string; title: string; score: number; completed_at: string }[];
  trend: Record<"accuracy" | "avg_words" | "exercise_accuracy", { recent: number | null; previous: number | null }>;
  totals: {
    user_messages: number;
    conversation_accuracy: number | null;
    exercise_accuracy: number | null;
    avg_words: number | null;
    lessons_completed: number;
  };
}

export interface CourseLessonSummary {
  id: string;
  title: string;
  objective: string;
  position: number;
  exercise_count: number;
  status: LessonStatus;
  locked: boolean;
  score: number | null;
  completed_at: string | null;
}

export interface CourseUnit {
  id: string;
  title: string;
  goal: string;
  lessons: CourseLessonSummary[];
}

export interface CourseLevel {
  code: Level;
  title: string;
  description: string;
  goal: string;
  completed: number;
  total: number;
  units: CourseUnit[];
}

export interface CourseOverview {
  language: { code: LanguageCode; name: string };
  levels: CourseLevel[];
  progress: { completed: number; total: number; percent: number };
  next_lesson_id: string | null;
  pass_score: number;
}

export interface CourseExercise {
  id: string;
  type: ExerciseType;
  prompt: string;
  context?: string;
  hint: string | null;
  answered: boolean;
  correct: boolean | null;
  last_answer: string | null;
  options?: string[];
  words?: string[];
  has_audio?: boolean;
}

export interface CourseLesson {
  id: string;
  title: string;
  objective: string;
  explanation: string;
  key_phrases: { en: string; pt: string }[];
  level: Level;
  unit_id: string;
  position: number;
  status: LessonStatus;
  locked: boolean;
  score: number | null;
  pass_score: number;
  answered: number;
  can_complete: boolean;
  exercises: CourseExercise[];
  next_lesson_id: string | null;
}

export interface CheckResult {
  correct: boolean;
  feedback_pt: string | null;
  correct_answer: string | null;
  used_ai_check: boolean;
}

export interface CompleteResult {
  score: number;
  passed: boolean;
  correct: number;
  total: number;
  pass_score: number;
  completed: boolean;
  next_lesson_id: string | null;
}

export interface SpeechStatus {
  reachable: boolean;
  stt_ready: boolean;
  tts_ready: boolean;
  message: string;
}

/** Lição criada pelo modelo, aguardando revisão do usuário (ainda fora da trilha). */
export interface CourseDraft {
  id: number;
  language: LanguageCode;
  level: Level;
  title: string;
  objective: string;
  explanation: string;
  key_phrases: { en: string; pt: string }[];
  exercises: { type: ExerciseType; prompt: string; explanation: string }[];
  created_at: string;
}

export interface DraftGeneration {
  drafts: CourseDraft[];
  failed: number;
  problems: string[];
}

/** Contexto do treino de repetição (resumo na lista). */
export interface DrillPackSummary {
  id: string;
  title: string;
  level: Level;
  context: string;
  sentence_count: number;
}

export interface DrillPacks {
  language: LanguageCode;
  packs: DrillPackSummary[];
}

export interface DrillPack extends DrillPackSummary {
  language: LanguageCode;
  sentences: { text: string; pt: string }[];
}

export interface DrillScore {
  expected: string;
  score: number;
  passed: boolean;
  missing: string[];
  extra: string[];
}

export interface AnalysisSummary {
  id: number;
  session_id: number;
  created_at: string;
  level_estimate: Level;
  confidence: "baixa" | "média" | "alta";
  declared_level: Level;
  student_turns: number;
  session_title: string;
}

export interface AnalysisEvidence {
  message_id: number;
  quote: string;
}

export interface LevelAnalysis {
  id: number;
  session_id: number;
  created_at: string;
  model: string;
  level_estimate: Level;
  confidence: "baixa" | "média" | "alta";
  level_reasoning_pt: string;
  level_vs_declared_pt: string;
  criteria: Record<"vocabulary" | "grammar" | "fluency" | "interaction" | "coherence", Level>;
  strengths: { text_pt: string; evidence: AnalysisEvidence }[];
  improvement_points: {
    priority: "alta" | "média" | "baixa";
    area: string;
    issue_pt: string;
    evidence: AnalysisEvidence;
    suggestion_pt: string;
    better_example: string;
    practice_pt: string;
  }[];
  transcription_doubts: { message_id: number; quote: string; note_pt: string }[];
  next_step_pt: string;
  student_turns: number;
  removed_citations: number;
}
