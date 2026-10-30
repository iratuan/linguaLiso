import { useEffect, useState } from "react";
import { BookOpenCheck, Languages, MessageCircle, Plus, Sparkles, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { api, describeError } from "../lib/api";
import {
  LANGUAGE_LABELS,
  type CourseOverview,
  type LanguageCode,
  type Profile,
  type Progress,
  type VocabularyCounts,
} from "../lib/types";
import { ErrorBanner, PageContainer } from "../components/ui";
import { Avatar, StatePill, Tile } from "../components/Tile";

const LANGUAGE_TONE: Record<LanguageCode, string> = {
  en: "from-sky-500 to-indigo-500",
  fr: "from-rose-500 to-amber-500",
};

function greeting(date: Date = new Date()): string {
  const h = date.getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export function HomePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [course, setCourse] = useState<CourseOverview | null>(null);
  const [vocab, setVocab] = useState<VocabularyCounts | null>(null);
  const [stats, setStats] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getProfile(), api.getSettings(), api.course(), api.listVocabulary(true), api.progress()])
      .then(([p, s, c, v, pr]) => {
        setProfile(p);
        setLanguage(s.target_language);
        setCourse(c);
        setVocab(v.counts);
        setStats(pr);
      })
      .catch((e) => setError(describeError(e)));
  }, []);

  const nextLesson = course?.next_lesson_id
    ? course.levels.flatMap((lv) => lv.units.flatMap((u) => u.lessons)).find((l) => l.id === course.next_lesson_id)
    : undefined;
  const firstName = profile?.display_name?.trim().split(" ")[0] || "aluno";
  const initials = (profile?.display_name?.trim() || "EL")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const percent = course?.progress.percent ?? 0;

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer wide>
        <header className="animate-rise flex flex-wrap items-end justify-between gap-6 pb-8">
          <div>
            <p className="eyebrow mb-2">
              {LANGUAGE_LABELS[language]} · {profile?.level ?? "A1"}
            </p>
            <h1 className="title-large">
              {greeting()}, {firstName}.
            </h1>
            <p className="mt-2 text-[15px] text-slate-400">
              {vocab && vocab.due > 0
                ? `${vocab.due} palavras aguardam revisão hoje.`
                : "Tudo revisado por hoje. Que tal avançar na trilha?"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/conversa" className="btn-primary">
              <Plus className="h-4 w-4" /> Nova conversa
            </Link>
            <div className="flex items-center gap-3 rounded-full border border-line bg-white/[0.04] py-1.5 pl-1.5 pr-4">
              <Avatar label={initials} />
              <span className="text-[14px] text-slate-300">{profile?.display_name || "Seu perfil"}</span>
            </div>
          </div>
        </header>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div className="grid gap-4 md:grid-cols-3">
          <Tile
            wide
            accent
            title={nextLesson ? nextLesson.title : "Trilha concluída"}
            subtitle={nextLesson ? `/trilhas/${nextLesson.id}` : "/trilhas"}
            to={nextLesson ? `/trilhas/${nextLesson.id}` : "/trilhas"}
            badge={<StatePill>Agora</StatePill>}
            progress={percent}
            footer={
              <>
                <span className="text-[13px] text-slate-400">
                  {course ? `${course.progress.completed} de ${course.progress.total} lições` : "Carregando…"}
                </span>
                <span className="text-[13px] font-medium text-slate-300">{percent}%</span>
              </>
            }
          >
            {nextLesson?.objective ?? "Continue de onde parou."}
          </Tile>

          <Tile
            title="Conversar"
            subtitle="/conversa"
            to="/conversa"
            badge={<Avatar label={language.toUpperCase()} tone={LANGUAGE_TONE[language]} />}
            footer={<span className="text-[13px] text-slate-400">{LANGUAGE_LABELS[language]} · voz e texto</span>}
          >
            Fale com o professor por voz ou texto. Ele corrige com cuidado.
          </Tile>

          <Tile
            title="Revisar vocabulário"
            subtitle="/vocabulario"
            to="/vocabulario"
            badge={vocab && vocab.due > 0 ? <StatePill>Hoje · {vocab.due}</StatePill> : undefined}
            footer={
              <span className="flex items-center gap-2 text-[13px] text-slate-400">
                <Languages className="h-4 w-4" /> {vocab ? `${vocab.total} palavras no total` : "Carregando…"}
              </span>
            }
          >
            Revise em sessões curtas, uma palavra por vez.
          </Tile>

          <Tile
            title="Progresso"
            subtitle="/progresso"
            to="/progresso"
            footer={
              <span className="flex items-center gap-2 text-[13px] text-slate-400">
                <TrendingUp className="h-4 w-4" />
                {stats ? `${stats.totals.sessions} conversas · ${stats.totals.user_messages} frases` : "Carregando…"}
              </span>
            }
          >
            Veja sua curva de aprendizado, precisão e evolução.
          </Tile>

          <Tile
            title="Aula sob medida"
            subtitle="/aulas"
            to="/aulas"
            footer={
              <span className="flex items-center gap-2 text-[13px] text-slate-400">
                <Sparkles className="h-4 w-4" /> Gerada pelo professor
              </span>
            }
          >
            Peça uma aula sobre qualquer tema do seu interesse.
          </Tile>
        </div>

        <p className="mt-10 flex items-center gap-2 text-[12px] text-slate-500">
          <BookOpenCheck className="h-3.5 w-3.5" /> Use Ctrl + 1 a 6 para navegar pelo menu.
          <MessageCircle className="ml-3 h-3.5 w-3.5" /> Tudo fica neste computador.
        </p>
      </PageContainer>
    </div>
  );
}
