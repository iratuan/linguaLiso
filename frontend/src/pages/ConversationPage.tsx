import { useCallback, useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import {
  CornerUpLeft,
  Headphones,
  History,
  Maximize2,
  MessageCircle,
  Mic,
  MicOff,
  Minimize2,
  Minus,
  PictureInPicture2,
  FileText,
  Loader2,
  Plus,
  Send,
  Square,
  Trash2,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api, describeError } from "../lib/api";
import { useServiceStatus } from "../hooks/useServiceStatus";
import { LEVEL_LABELS } from "../lib/format";
import {
  LANGUAGE_LABELS,
  MODE_LABELS,
  PERSONA_DESCRIPTIONS,
  PERSONA_LABELS,
  SCENARIO_LABELS,
  type CorrectionData,
  type LanguageCode,
  type Level,
  type Message,
  type Mode,
  type NewVocabulary,
  type Profile,
  type Session,
  type Settings,
  type StudyMaterial,
  type TeacherPersona,
} from "../lib/types";
import { CorrectionCard, MessageBubble, NewVocabularyChips, TypingIndicator } from "../components/conversation";
import { StudyMaterialSheet } from "../components/StudyMaterialSheet";
import { EmptyState, ErrorBanner, PageHeader, Segmented, Spinner, VoiceMeter } from "../components/ui";
import { MAX_RECORDING_MS, usePlayback, useRecorder } from "../hooks/useVoice";

const MODES = Object.keys(MODE_LABELS) as Mode[];
const SCENARIOS = Object.keys(SCENARIO_LABELS);
const LEVELS = Object.keys(LEVEL_LABELS) as Level[];

type Tone = "ok" | "busy" | "warn" | "error";

const TONE_DOT: Record<Tone, string> = {
  ok: "bg-ios-green",
  busy: "bg-brand-400 animate-pulse",
  warn: "bg-ios-orange",
  error: "bg-ios-red",
};

/**
 * "page": tela inteira da conversa. "open": janela flutuante no canto inferior direito.
 * "max": janela flutuante ocupando a área de conteúdo. "closed": só o botão para abrir.
 */
/** "window": a conversa numa janela própria do Electron, sempre no topo. */
export type ChatPresentation = "page" | "open" | "max" | "closed" | "window";

export function ConversationPage({
  presentation = "page",
  onPresentation,
}: {
  presentation?: ChatPresentation;
  onPresentation?: (next: ChatPresentation) => void;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [corrections, setCorrections] = useState<Record<number, CorrectionData>>({});
  const [vocabulary, setVocabulary] = useState<Record<number, NewVocabulary[]>>({});
  const [mode, setMode] = useState<Mode>("free");
  const [scenario, setScenario] = useState<string>(SCENARIOS[0]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [starting, setStarting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [material, setMaterial] = useState<StudyMaterial | null>(null);
  const [materialBusy, setMaterialBusy] = useState(false);
  const [devices, setDevices] = useState({ input: true, output: true });
  const services = useServiceStatus();
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const playback = usePlayback(
    {
      voice: settings?.speech_voice,
      rate: settings?.speech_rate ?? 1,
      volume: settings?.speech_volume ?? 1,
    },
    setError,
  );

  const responseMode = settings?.response_mode ?? "audio";
  // Refs para o envio ler sempre o valor atual sem recriar callbacks.
  const responseModeRef = useRef<"audio" | "text">("audio");
  responseModeRef.current = responseMode;
  const playbackRef = useRef(playback.speak);
  playbackRef.current = playback.speak;
  // Quantas respostas do professor já foram vistas (o aviso do botão minimizado conta as demais).
  const seenAssistant = useRef(0);

  // ----- dados ------------------------------------------------------------

  const loadTranscript = useCallback(async (sessionId: number) => {
    const transcript = await api.getSession(sessionId);
    setMessages(transcript.messages);
    // Respostas do histórico já existiam: não são novidades para o aviso.
    seenAssistant.current = transcript.messages.filter((m) => m.role === "assistant").length;
    const byMessage: Record<number, CorrectionData> = {};
    for (const c of transcript.corrections) byMessage[c.message_id] = c;
    setCorrections(byMessage);
    setVocabulary({});
    setMode(transcript.session.mode);
    if (transcript.session.scenario) setScenario(transcript.session.scenario);
    setSession(transcript.session);
  }, []);

  const startSession = useCallback(
    async (nextMode: Mode, nextScenario?: string) => {
      setError(null);
      if (session && !session.ended_at) {
        await api.endSession(session.id).catch(() => undefined);
      }
      const created = await api.createSession(nextMode, nextScenario);
      setSession(created);
      setMode(created.mode);
      setMessages([]);
      setCorrections({});
      setVocabulary({});
    },
    [session],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [loadedProfile, loadedSettings, sessions] = await Promise.all([
          api.getProfile(),
          api.getSettings(),
          api.listSessions(),
        ]);
        if (cancelled) return;
        setProfile(loadedProfile);
        setSettings(loadedSettings);
        // Reaproveita a conversa aberta só se ela for do idioma que o aluno estuda agora.
        const open = sessions.find((s) => s.ended_at === null && s.language === loadedSettings.target_language);
        if (open) await loadTranscript(open.id);
        else {
          const created = await api.createSession("free");
          if (!cancelled) setSession(created);
        }
      } catch (e) {
        if (!cancelled) setError(describeError(e));
      } finally {
        if (!cancelled) setStarting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carregamento inicial único
  }, []);

  useEffect(() => {
    navigator.mediaDevices
      ?.enumerateDevices()
      .then((list) =>
        setDevices({
          input: list.some((d) => d.kind === "audioinput"),
          output: list.some((d) => d.kind === "audiooutput"),
        }),
      )
      .catch(() => setDevices({ input: false, output: false }));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, thinking]);

  // ----- envio ------------------------------------------------------------

  const send = useCallback(
    async (content: string, source: "text" | "voice") => {
      const text = content.trim();
      if (!session || thinking || !text) return;
      setError(null);
      setThinking(true);
      const optimisticId = -Date.now();
      setMessages((prev) => [
        ...prev,
        { id: optimisticId, role: "user", content: text, input_source: source, created_at: new Date().toISOString() },
      ]);
      setDraft("");
      try {
        const turn = await api.sendMessage(session.id, text, source);
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== optimisticId),
          {
            id: turn.user_message_id,
            role: "user",
            content: text,
            input_source: source,
            created_at: new Date().toISOString(),
          },
          turn.assistant_message,
        ]);
        if (turn.correction) {
          const { id: _id, ...correction } = turn.correction;
          void _id;
          setCorrections((prev) => ({ ...prev, [turn.user_message_id]: correction }));
        }
        if (turn.new_vocabulary.length > 0) {
          setVocabulary((prev) => ({ ...prev, [turn.user_message_id]: turn.new_vocabulary }));
        }
        // Modo padrão: o professor responde em voz. Em "text", só o texto aparece.
        if (responseModeRef.current === "audio") {
          void playbackRef.current(turn.assistant_message.content);
        }
      } catch (e) {
        setError(describeError(e));
        // A mensagem do aluno pode ter sido salva mesmo com falha da LLM: sincroniza com o banco.
        await loadTranscript(session.id).catch(() => undefined);
      } finally {
        setThinking(false);
      }
    },
    [session, thinking, loadTranscript],
  );

  const recorder = useRecorder((text, meta) => {
    // Quando o aluno para de falar (silêncio), a mensagem é enviada direto.
    if (!meta.bySilence && (settings?.confirm_transcription ?? true)) {
      setDraft(text);
      textareaRef.current?.focus();
    } else {
      void send(text, "voice");
    }
  }, setError);

  // Gravar com a voz do professor tocando captaria a própria resposta: a reprodução para antes.
  const toggleRecord = () => {
    if (recorder.state === "idle" && playback.state !== "idle") playback.stop();
    recorder.toggle();
  };

  // ----- ações ------------------------------------------------------------

  const changeMode = async (nextMode: Mode) => {
    if (nextMode === mode && session) return;
    try {
      await startSession(nextMode, nextMode === "roleplay" ? scenario : undefined);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const changeScenario = async (next: string) => {
    setScenario(next);
    try {
      await startSession("roleplay", next);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const changeLanguage = async (language: LanguageCode) => {
    if (!settings || language === settings.target_language) return;
    try {
      setSettings(await api.updateSettings({ target_language: language }));
      // Cada idioma tem a sua conversa: começa uma nova no idioma escolhido.
      await startSession(mode, mode === "roleplay" ? scenario : undefined);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const changePersona = async (persona: TeacherPersona) => {
    if (!settings || persona === (session?.persona ?? settings.teacher_persona)) return;
    try {
      setSettings(await api.updateSettings({ teacher_persona: persona }));
      // Cada conversa guarda a personalidade com que começou: troca-se começando uma nova.
      await startSession(mode, mode === "roleplay" ? scenario : undefined);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const changeLevel = async (level: Level) => {
    if (!profile) return;
    try {
      const saved = await api.saveProfile({ ...profile, level });
      setProfile(saved);
      await startSession(mode, mode === "roleplay" ? scenario : undefined);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const changeResponseMode = async (value: "audio" | "text") => {
    if (!settings) return;
    try {
      setSettings(await api.updateSettings({ response_mode: value }));
      if (value === "text") playback.stop();
    } catch (e) {
      setError(describeError(e));
    }
  };

  // ----- histórico ----------------------------------------------------------

  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<Session[] | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const toggleHistory = async () => {
    if (historyOpen) {
      setHistoryOpen(false);
      return;
    }
    setHistoryOpen(true);
    setHistory(null);
    setConfirmDelete(null);
    try {
      setHistory(await api.listSessions());
    } catch (e) {
      setError(describeError(e));
      setHistoryOpen(false);
    }
  };

  const openSession = async (id: number) => {
    setHistoryOpen(false);
    try {
      await loadTranscript(id);
    } catch (e) {
      setError(describeError(e));
    }
  };

  const removeSession = async (id: number) => {
    try {
      await api.deleteSession(id);
      setHistory((prev) => prev?.filter((s) => s.id !== id) ?? null);
      setConfirmDelete(null);
      if (session?.id === id) {
        // Apagou a conversa aberta: começa uma nova no lugar dela.
        setSession(null);
        setMessages([]);
        await newConversation();
      }
    } catch (e) {
      setError(describeError(e));
    }
  };

  const makeMaterial = async () => {
    if (!session) return;
    setError(null);
    setMaterialBusy(true);
    try {
      setMaterial(await api.studyMaterial(session.id));
    } catch (e) {
      setError(describeError(e));
    } finally {
      setMaterialBusy(false);
    }
  };

  const newConversation = async () => {
    try {
      await startSession(mode, mode === "roleplay" ? scenario : undefined);
    } catch (e) {
      setError(describeError(e));
    }
  };

  // ----- derivados --------------------------------------------------------

  const busy = thinking || recorder.state !== "idle" || starting;
  const persona: TeacherPersona = session?.persona ?? settings?.teacher_persona ?? "descontraido";
  const micUnavailable = Boolean(recorder.micError) || !devices.input;

  /** Uma única linha de estado, sempre acima da digitação. Prioridade: o que está acontecendo agora. */
  const status: { text: string; tone: Tone } = (() => {
    if (recorder.state === "recording")
      return { text: "Ouvindo você. Pare de falar ou toque em parar para enviar", tone: "error" };
    if (recorder.state === "transcribing") return { text: "Reconhecendo sua fala", tone: "busy" };
    if (thinking) return { text: "O professor está pensando", tone: "busy" };
    if (playback.state === "generating") return { text: "Preparando a voz", tone: "busy" };
    if (playback.state === "playing") return { text: "Reproduzindo a resposta", tone: "ok" };
    if (recorder.micError) return { text: recorder.micError.message, tone: "error" };
    if (!devices.input) return { text: "Nenhum microfone encontrado", tone: "warn" };
    if (services.llm === "down") return { text: "Ollama não responde. Verifique se ele está aberto", tone: "error" };
    if (services.llm === "warning") return { text: "Modelo de linguagem não instalado", tone: "warn" };
    return { text: "Pronto para conversar", tone: "ok" };
  })();

  // Respostas que chegaram enquanto a janela estava minimizada (aparecem como aviso no botão).
  const assistantCount = messages.filter((m) => m.role === "assistant").length;
  useEffect(() => {
    if (presentation !== "closed") seenAssistant.current = assistantCount;
  }, [presentation, assistantCount]);
  const unreadReplies = presentation === "closed" ? Math.max(0, assistantCount - seenAssistant.current) : 0;

  // ----- render -----------------------------------------------------------

  if (presentation === "closed") {
    return (
      <button
        type="button"
        onClick={() => onPresentation?.("open")}
        aria-label={unreadReplies > 0 ? `Professor: ${unreadReplies} nova(s) resposta(s)` : "Abrir o professor"}
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2.5 rounded-full border border-line bg-white/[0.08] py-3 pl-4 pr-5 text-[14px] font-medium text-white shadow-2xl backdrop-blur-2xl transition hover:bg-white/[0.14]"
      >
        <span className="relative">
          <MessageCircle className="h-4 w-4 text-brand-300" />
          {unreadReplies > 0 && (
            <span
              className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-ios-green ring-2 ring-surface-2"
              aria-hidden
            />
          )}
        </span>
        Professor
        {unreadReplies > 0 && <span className="text-[12px] font-normal text-ios-green">nova resposta</span>}
      </button>
    );
  }

  const isWidget = presentation !== "page";
  const showFull = presentation !== "open" && presentation !== "window"; // compacto: sem cabeçalho e preferências
  const chatBridge = window.englishTeacher?.chat; // existe só dentro do app desktop
  const inOwnWindow = presentation === "window";

  const shellClass =
    presentation === "page"
      ? "flex min-h-0 flex-1 flex-col"
      : presentation === "window"
        ? "flex h-screen w-screen flex-col overflow-hidden bg-[rgba(14,14,20,0.16)]"
        : presentation === "max"
          ? "fixed inset-y-6 right-6 left-[276px] z-40 flex flex-col overflow-hidden rounded-[26px] border border-white/10 bg-[rgba(20,20,28,0.4)] shadow-2xl shadow-black/40 backdrop-blur-3xl animate-sheet"
          : "fixed bottom-6 right-6 z-40 flex h-[min(560px,calc(100vh-7rem))] w-[380px] flex-col overflow-hidden rounded-[26px] border border-white/10 bg-[rgba(20,20,28,0.35)] shadow-2xl shadow-black/40 backdrop-blur-3xl animate-sheet";

  return (
    <div
      className={shellClass}
      // Escape recolhe a janela; a conversa continua de onde parou.
      onKeyDown={(e) => {
        if (e.key === "Escape" && (presentation === "open" || presentation === "max")) onPresentation?.("closed");
      }}
    >
      {isWidget && (
        <div
          className={`flex shrink-0 items-center justify-between gap-3 border-b border-line py-3 ${
            inOwnWindow ? "drag-region pl-5 pr-[150px]" : "px-5"
          }`}
        >
          <div className="min-w-0">
            <p className="text-[15px] font-semibold text-white">Professor</p>
            <p className="truncate text-[12px] text-slate-500">{session?.title ?? "Conversa"}</p>
          </div>
          <div className="no-drag flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              onClick={() => void newConversation()}
              disabled={busy}
              aria-label="Nova conversa"
              title="Nova conversa"
              className="icon-btn !h-8 !w-8"
            >
              <Plus className="h-4 w-4" />
            </button>
            {chatBridge && !inOwnWindow && (
              <button
                type="button"
                onClick={() => void chatBridge.popout()}
                aria-label="Abrir em janela flutuante"
                title="Abrir em janela flutuante (fica por cima de outros programas)"
                className="icon-btn !h-8 !w-8"
              >
                <PictureInPicture2 className="h-4 w-4" />
              </button>
            )}
            {inOwnWindow && chatBridge && (
              <button
                type="button"
                onClick={() => void chatBridge.restore()}
                aria-label="Voltar ao app"
                title="Voltar ao app"
                className="inline-flex h-8 items-center gap-1.5 rounded-full border border-line bg-white/[0.06] px-3 text-[12px] font-medium text-slate-200 hover:bg-white/[0.12]"
              >
                <CornerUpLeft className="h-3.5 w-3.5" /> Voltar ao app
              </button>
            )}
            {inOwnWindow ? null : presentation === "open" ? (
              <button
                type="button"
                onClick={() => onPresentation?.("max")}
                aria-label="Maximizar"
                title="Maximizar"
                className="icon-btn !h-8 !w-8"
              >
                <Maximize2 className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onPresentation?.("open")}
                aria-label="Restaurar tamanho"
                title="Restaurar tamanho"
                className="icon-btn !h-8 !w-8"
              >
                <Minimize2 className="h-4 w-4" />
              </button>
            )}
            {!inOwnWindow && (
              <button
                type="button"
                onClick={() => onPresentation?.("closed")}
                aria-label="Minimizar"
                title="Minimizar"
                className="icon-btn !h-8 !w-8"
              >
                <Minus className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}
      <div className={isWidget ? "shrink-0 px-5 pt-2" : "px-10 pt-9"}>
        {showFull && (
          <PageHeader
            path="/conversa"
            eyebrow={session?.title ?? "Conversa"}
            title="Conversa"
            subtitle={
              profile
                ? [
                    LEVEL_LABELS[profile.level],
                    // A variante (americano ou britânico) só existe para o inglês.
                    (settings?.target_language ?? "en") === "en"
                      ? profile.english_variant === "american"
                        ? "inglês americano"
                        : "inglês britânico"
                      : LANGUAGE_LABELS.fr,
                  ].join(" · ")
                : undefined
            }
            actions={
              <>
                {chatBridge && (
                  <button type="button" className="btn-ghost" onClick={() => void chatBridge.popout()}>
                    <PictureInPicture2 className="h-4 w-4" /> Janela flutuante
                  </button>
                )}
                <button type="button" className="btn-ghost" onClick={() => void toggleHistory()}>
                  <History className="h-4 w-4" /> Conversas
                </button>
                <button type="button" className="btn-ghost" onClick={() => void newConversation()} disabled={busy}>
                  <Plus className="h-4 w-4" /> Nova conversa
                </button>
              </>
            }
          />
        )}

        {showFull && (
          /* Faixa de preferências: tudo que muda a conversa, em uma única linha. */
          <div className="-mt-3 mb-2 flex flex-wrap items-center gap-x-5 gap-y-3 border-b border-line pb-5">
            <InlineSelect
              label="Idioma"
              value={settings?.target_language ?? "en"}
              onChange={(v) => void changeLanguage(v as LanguageCode)}
              disabled={busy || !settings}
            >
              <option value="en">{LANGUAGE_LABELS.en}</option>
              <option value="fr">{LANGUAGE_LABELS.fr}</option>
            </InlineSelect>

            <InlineSelect label="Modo" value={mode} onChange={(v) => void changeMode(v as Mode)} disabled={busy}>
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {MODE_LABELS[m]}
                </option>
              ))}
            </InlineSelect>

            <InlineSelect
              label="Professor"
              value={persona}
              onChange={(v) => void changePersona(v as TeacherPersona)}
              disabled={busy || !settings}
            >
              {(Object.keys(PERSONA_LABELS) as TeacherPersona[]).map((p) => (
                <option key={p} value={p} title={PERSONA_DESCRIPTIONS[p]}>
                  {PERSONA_LABELS[p]}
                </option>
              ))}
            </InlineSelect>

            {mode === "roleplay" && (
              <InlineSelect label="Cenário" value={scenario} onChange={(v) => void changeScenario(v)} disabled={busy}>
                {SCENARIOS.map((s) => (
                  <option key={s} value={s}>
                    {SCENARIO_LABELS[s]}
                  </option>
                ))}
              </InlineSelect>
            )}

            <InlineSelect
              label="Nível"
              value={profile?.level ?? "A1"}
              onChange={(v) => void changeLevel(v as Level)}
              disabled={!profile || busy}
            >
              {LEVELS.map((l) => (
                <option key={l} value={l}>
                  {LEVEL_LABELS[l]}
                </option>
              ))}
            </InlineSelect>

            <div className="ml-auto">
              <Segmented
                label="Resposta do professor"
                value={responseMode}
                onChange={(v) => void changeResponseMode(v)}
                options={[
                  { value: "audio", label: "Voz" },
                  { value: "text", label: "Texto" },
                ]}
              />
            </div>
          </div>
        )}

        {showFull && profile === null && !starting && (
          <p className="mt-4 text-[13px] text-slate-400">
            Defina seu nome e nível em{" "}
            <Link className="text-brand-300 hover:text-brand-200" to="/configuracoes">
              Ajustes
            </Link>{" "}
            para o professor adaptar a conversa.
          </p>
        )}
        <div className="mt-4">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />

          {historyOpen && (
            <div className="animate-rise fixed right-8 top-24 z-40 flex max-h-[62vh] w-[380px] flex-col overflow-hidden rounded-[22px] border border-line bg-surface-2/95 shadow-2xl backdrop-blur-2xl">
              <div className="flex items-center justify-between border-b border-line px-5 py-3">
                <p className="text-[15px] font-semibold text-white">Conversas</p>
                <button
                  type="button"
                  className="text-[20px] leading-none text-slate-400 hover:text-white"
                  onClick={() => setHistoryOpen(false)}
                  aria-label="Fechar histórico"
                >
                  ×
                </button>
              </div>
              <div className="overflow-y-auto">
                {history === null && <Spinner label="Carregando…" />}
                {history?.length === 0 && (
                  <p className="px-5 py-6 text-[14px] text-slate-400">Nenhuma conversa ainda.</p>
                )}
                {history?.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center gap-3 border-b border-line px-5 py-3 last:border-0 ${
                      item.id === session?.id ? "bg-white/[0.06]" : ""
                    }`}
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => void openSession(item.id)}
                    >
                      <p className="truncate text-[14px] text-white">{item.title || "Conversa"}</p>
                      <p className="text-[12px] text-slate-500">
                        {new Date(item.started_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}{" "}
                        · {item.message_count ?? 0} mensagens{item.ended_at ? "" : " · aberta"}
                      </p>
                    </button>
                    {confirmDelete === item.id ? (
                      <div className="flex shrink-0 gap-2">
                        <button
                          type="button"
                          className="btn-danger !py-1.5 text-[13px]"
                          onClick={() => void removeSession(item.id)}
                        >
                          Apagar
                        </button>
                        <button
                          type="button"
                          className="btn-ghost !py-1.5 text-[13px]"
                          onClick={() => setConfirmDelete(null)}
                        >
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="icon-btn !h-8 !w-8 shrink-0"
                        onClick={() => setConfirmDelete(item.id)}
                        aria-label={`Apagar conversa ${item.title || ""}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={`flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto ${isWidget ? "px-5 py-4" : "px-10 py-6"}`}>
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {messages.length === 0 && !starting && (
            <EmptyState icon={<Headphones className="h-6 w-6" />} title="Vamos praticar?">
              Escreva ou fale uma frase em inglês. Eu respondo, corrijo com cuidado e guardo as palavras novas no seu
              vocabulário.
              {mode === "roleplay" && (
                <p className="mt-2">Estou no papel de {SCENARIO_LABELS[scenario]?.toLowerCase()}.</p>
              )}
            </EmptyState>
          )}

          {messages.map((message) => {
            const correction = message.role === "user" ? corrections[message.id] : undefined;
            const vocab = message.role === "user" ? vocabulary[message.id] : undefined;
            return (
              <MessageBubble
                key={message.id}
                message={message}
                onSpeak={message.role === "assistant" ? (text) => void playback.speak(text) : undefined}
                speaking={playback.state !== "idle"}
                persona={message.role === "assistant" ? persona : undefined}
              >
                {correction && (
                  <div className="self-start">
                    <CorrectionCard
                      correction={correction}
                      onRepeat={(text) => void playback.speak(text)}
                      repeating={playback.state !== "idle"}
                    />
                  </div>
                )}
                {vocab && vocab.length > 0 && <NewVocabularyChips items={vocab} />}
              </MessageBubble>
            );
          })}

          {thinking && <TypingIndicator label="Preparando resposta…" />}
          {recorder.state === "transcribing" && <TypingIndicator label="Reconhecendo sua fala…" />}
          <div ref={endRef} />
        </div>
      </div>

      {material && <StudyMaterialSheet material={material} onClose={() => setMaterial(null)} />}

      <div className={isWidget ? "glass shrink-0 px-5 pb-4 pt-3" : "glass px-10 pb-6 pt-4"}>
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-2 flex min-h-[20px] items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-[12px] text-slate-400" role="status" aria-live="polite">
              <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[status.tone]}`} aria-hidden />
              {status.text}
            </p>
            <div className="flex items-center gap-2">
              {playback.state !== "idle" && (
                <button
                  type="button"
                  onClick={playback.stop}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.08] px-3 py-1 text-[12px] font-medium text-slate-200 transition hover:bg-white/[0.14]"
                >
                  <Square className="h-3 w-3 fill-current" /> Parar voz
                </button>
              )}
              {session && messages.some((m) => m.role === "user") && (
                <button
                  type="button"
                  onClick={() => void makeMaterial()}
                  disabled={busy || materialBusy}
                  title="Gera um exercício com lacunas a partir desta conversa, para imprimir"
                  className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.08] px-3 py-1 text-[12px] font-medium text-slate-200 transition hover:bg-white/[0.14] disabled:opacity-40"
                >
                  {materialBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
                  {materialBusy ? "Montando material…" : "Material de apoio"}
                </button>
              )}
            </div>
          </div>
          <Composer
            textareaRef={textareaRef}
            draft={draft}
            onChange={setDraft}
            // Enter também passa por aqui: não envia enquanto o microfone está ocupado.
            onSend={() => {
              if (recorder.state === "idle") void send(draft, "text");
            }}
            onToggleRecord={toggleRecord}
            recording={recorder.state === "recording"}
            level={recorder.level}
            elapsedMs={recorder.elapsedMs}
            recorderBusy={recorder.state === "transcribing"}
            disabled={busy || !session}
            micDisabled={thinking || starting || !session}
            micUnavailable={micUnavailable}
            confirmTranscription={settings?.confirm_transcription ?? true}
          />
          <p className="mt-2 text-center text-[11px] text-slate-600">
            Enter envia · Shift+Enter quebra linha · Processado no seu computador
          </p>
        </div>
      </div>
    </div>
  );
}

/** Seletor discreto com rótulo: texto pequeno à esquerda e o valor em destaque. */
function InlineSelect({
  label,
  value,
  onChange,
  disabled,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="flex items-center gap-2.5 rounded-full border border-line bg-white/[0.04] py-1.5 pl-4 pr-2 text-[13px] transition hover:bg-white/[0.07]">
      <span className="text-slate-500">{label}</span>
      <select
        aria-label={label}
        className="cursor-pointer bg-transparent pr-2 font-medium text-slate-100 focus:outline-none disabled:cursor-default disabled:opacity-50 [&>option]:bg-surface-2"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {children}
      </select>
    </label>
  );
}

function Composer({
  textareaRef,
  draft,
  onChange,
  onSend,
  onToggleRecord,
  recording,
  level,
  elapsedMs,
  recorderBusy,
  disabled,
  micDisabled,
  micUnavailable,
  confirmTranscription,
}: {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  draft: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onToggleRecord: () => void;
  recording: boolean;
  level: number;
  elapsedMs: number;
  recorderBusy: boolean;
  disabled: boolean;
  micDisabled: boolean;
  micUnavailable: boolean;
  confirmTranscription: boolean;
}) {
  return (
    <div className="flex items-end gap-2 rounded-[26px] border border-line bg-white/[0.06] p-2 shadow-lg shadow-black/30 backdrop-blur-2xl transition focus-within:border-white/20">
      <button
        type="button"
        onClick={onToggleRecord}
        // Enquanto grava, o botão continua ativo para poder parar.
        disabled={recording ? false : micDisabled || recorderBusy || micUnavailable}
        aria-pressed={recording}
        aria-label={recording ? "Parar gravação" : "Gravar voz"}
        title={micUnavailable ? "Microfone indisponível" : recording ? "Parar gravação" : "Gravar voz"}
        className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white transition-colors duration-300 active:scale-95 disabled:opacity-35 ${
          recording ? "bg-ios-red shadow-[0_0_0_4px_rgba(255,69,58,0.25)]" : "bg-white/[0.08] hover:bg-white/[0.14]"
        }`}
      >
        {micUnavailable ? (
          <MicOff className="h-[18px] w-[18px]" />
        ) : recording ? (
          <Square className="h-4 w-4 fill-current" />
        ) : (
          <Mic className="h-[18px] w-[18px]" />
        )}
      </button>

      {recording && (
        <div className="flex min-h-[44px] flex-1 items-center px-3 py-2.5">
          <VoiceMeter level={level} elapsedMs={elapsedMs} maxMs={MAX_RECORDING_MS} />
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={draft}
        rows={1}
        // Durante a gravação o medidor ocupa o lugar do campo; o rascunho continua guardado.
        hidden={recording}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder={confirmTranscription ? "Escreva em inglês ou grave sua voz…" : "Escreva em inglês…"}
        className="max-h-40 min-h-[44px] w-full resize-none bg-transparent px-2 py-2.5 text-[16px] leading-relaxed text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
        aria-label="Mensagem para o professor"
      />

      <button
        type="button"
        className="flex h-11 shrink-0 items-center gap-2 rounded-full bg-brand-500 px-5 text-[14px] font-medium text-on-accent shadow-md shadow-brand-500/25 transition duration-300 hover:bg-brand-400 active:scale-[0.97] disabled:bg-white/[0.08] disabled:text-slate-500 disabled:shadow-none"
        onClick={onSend}
        disabled={disabled || !draft.trim() || recording}
        aria-label="Enviar mensagem"
      >
        <Send className="h-4 w-4" /> Enviar
      </button>
    </div>
  );
}
