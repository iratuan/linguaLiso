import { useEffect, useRef, useState } from "react";
import { HashRouter, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  Home,
  Languages,
  MessageCircle,
  Settings as SettingsIcon,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { api } from "./lib/api";
import { applyAppearance } from "./lib/appearance";
import logoMark from "./assets/logo-mark.png";
import { useServiceStatus, type ServiceState } from "./hooks/useServiceStatus";
import { Avatar } from "./components/Tile";
import { HomePage } from "./pages/HomePage";
import { ConversationPage, type ChatPresentation } from "./pages/ConversationPage";
import { CoursePage } from "./pages/CoursePage";
import { DrillsPage } from "./pages/DrillsPage";
import { LessonPlayerPage } from "./pages/LessonPlayerPage";
import { LessonsPage } from "./pages/LessonsPage";
import { ProgressPage } from "./pages/ProgressPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VocabularyPage } from "./pages/VocabularyPage";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

// Ordem do menu = atalhos Ctrl+1 a Ctrl+6.
const NAV: NavItem[] = [
  { to: "/inicio", label: "Início", icon: Home },
  { to: "/trilhas", label: "Trilhas", icon: BookOpenCheck },
  { to: "/conversa", label: "Conversa", icon: MessageCircle },
  { to: "/aulas", label: "Aula sob medida", icon: Sparkles },
  { to: "/vocabulario", label: "Vocabulário", icon: Languages },
  { to: "/progresso", label: "Progresso", icon: TrendingUp },
];

/** Conteúdo das telas. A conversa não é uma rota comum: ela fica sempre montada (ver ChatHost). */
function Content() {
  const { pathname } = useLocation();
  const inChat = pathname.startsWith("/conversa");
  return (
    <>
      <div className={inChat ? "hidden" : "flex min-h-0 flex-1 flex-col"}>
        <Routes>
          <Route path="/" element={<Navigate to="/inicio" replace />} />
          <Route path="/inicio" element={<HomePage />} />
          <Route path="/trilhas" element={<CoursePage />} />
          <Route path="/trilhas/:lessonId" element={<LessonPlayerPage />} />
          <Route path="/treino" element={<DrillsPage />} />
          <Route path="/treino/:packId" element={<DrillsPage />} />
          {/* A rota existe para não cair no curinga; o conteúdo é a própria ChatHost. */}
          <Route path="/conversa" element={null} />
          <Route path="/aulas" element={<LessonsPage />} />
          <Route path="/vocabulario" element={<VocabularyPage />} />
          <Route path="/progresso" element={<ProgressPage />} />
          <Route path="/configuracoes" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/inicio" replace />} />
        </Routes>
      </div>
      <ChatHost />
    </>
  );
}

/**
 * Professor: na rota /conversa aparece em tela inteira; nas outras telas, como janela flutuante.
 * Ao sair da conversa, ela continua aberta como janela, sem perder o que estava sendo feito.
 */
const WIDGET_KEY = "chat-widget-state";

/** Estado da janela do professor (aberta, maximizada ou minimizada), lembrado neste computador. */
function readWidgetState(): ChatPresentation {
  try {
    const saved = window.localStorage.getItem(WIDGET_KEY);
    return saved === "open" || saved === "max" || saved === "closed" ? saved : "closed";
  } catch {
    return "closed";
  }
}

function ChatHost() {
  const { pathname } = useLocation();
  const inChat = pathname.startsWith("/conversa");
  const [widget, setWidget] = useState<ChatPresentation>(readWidgetState);
  const wasInChat = useRef(inChat);

  useEffect(() => {
    if (wasInChat.current && !inChat) setWidget((current) => (current === "closed" ? "open" : current));
    wasInChat.current = inChat;
  }, [inChat]);

  useEffect(() => {
    try {
      window.localStorage.setItem(WIDGET_KEY, widget === "page" ? "closed" : widget);
    } catch {
      // Sem armazenamento disponível, a janela simplesmente não lembra o estado.
    }
  }, [widget]);

  return <ConversationPage presentation={inChat ? "page" : widget} onPresentation={setWidget} />;
}

/**
 * Janela flutuante do professor (rota /chat-window, aberta pelo Electron): só a conversa,
 * sem o menu. A janela principal fica minimizada enquanto ela existe.
 */
function Shell() {
  const { pathname } = useLocation();
  // Aplica a aparência salva em Ajustes logo ao abrir o app (e na janela do professor).
  useEffect(() => {
    api
      .getSettings()
      .then((s) => applyAppearance({ transparency: s.ui_transparency, theme: s.app_theme }))
      .catch(() => undefined);
  }, []);
  if (pathname.startsWith("/chat-window")) return <ConversationPage presentation="window" />;
  return (
    <div className="flex h-full">
      <Sidebar />
      <main className="content-surface flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Faixa arrastável da janela (a janela não tem a barra cinza do Windows). */}
        <div className="drag-region h-9 shrink-0" aria-hidden />
        <Content />
      </main>
    </div>
  );
}

export function App() {
  return (
    // HashRouter: funciona com o app carregado via file:// no Electron empacotado.
    <HashRouter>
      <Shell />
    </HashRouter>
  );
}

/** Ctrl+1 a Ctrl+6 levam às telas do menu, como os atalhos da referência. */
function useNavigationShortcuts() {
  const navigate = useNavigate();
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return;
      const index = Number(event.key) - 1;
      if (Number.isInteger(index) && index >= 0 && index < NAV.length) {
        event.preventDefault();
        navigate(NAV[index].to);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
}

function Sidebar() {
  useNavigationShortcuts();
  return (
    <aside className="sidebar-surface flex w-[244px] shrink-0 flex-col border-r border-line px-3 pb-4 pt-3 backdrop-blur-2xl">
      {/* Marca no topo: logo grande com o nome abaixo. A área é de arrasto, sob os controles da janela */}
      <div className="drag-region flex flex-col items-center gap-2 px-2 pb-4 pt-2">
        <img src={logoMark} alt="" aria-hidden className="no-drag h-14 w-14 shrink-0 object-contain" />
        <p className="no-drag text-[16px] font-semibold tracking-tight text-white">English Teacher</p>
      </div>
      <div className="mx-2 border-t border-line" aria-hidden />

      <nav className="mt-4 flex flex-1 flex-col gap-0.5" aria-label="Navegação principal">
        {NAV.map(({ to, label, icon: Icon }, index) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-[10px] px-3 py-2 text-[14px] font-medium transition duration-200 ${
                isActive ? "bg-white/[0.11] text-white" : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-100"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  className={`h-4 w-4 transition ${isActive ? "text-brand-300" : "text-slate-500 group-hover:text-slate-300"}`}
                />
                <span className="flex-1 truncate">{label}</span>
                <kbd className="rounded-md border border-line px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                  Ctrl {index + 1}
                </kbd>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="flex flex-col gap-1 border-t border-line pt-3">
        <UserBlock />
        <SystemStatus />
        <NavLink
          to="/configuracoes"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-[10px] px-3 py-2 text-[14px] font-medium transition duration-200 ${
              isActive ? "bg-white/[0.11] text-white" : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-100"
            }`
          }
        >
          <SettingsIcon className="h-4 w-4 text-slate-500" />
          Ajustes
        </NavLink>
      </div>
    </aside>
  );
}

/** Avatar com as iniciais do aluno e o nome, como o usuário da referência. */
function UserBlock() {
  const [name, setName] = useState("");
  useEffect(() => {
    api
      .getProfile()
      .then((p) => setName(p?.display_name?.trim() ?? ""))
      .catch(() => setName(""));
  }, []);
  const initials = (name || "EL")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <NavLink
      to="/configuracoes"
      className="flex items-center gap-2.5 rounded-[10px] px-3 py-2 transition hover:bg-white/[0.05]"
    >
      <Avatar label={initials} />
      <span className="truncate text-[13px] text-slate-200">{name || "Seu perfil"}</span>
    </NavLink>
  );
}

/** Um resumo único do estado local. Os detalhes técnicos ficam em Ajustes → Diagnóstico. */
function SystemStatus() {
  const { backend, llm, speech, details } = useServiceStatus();
  const states: ServiceState[] = [backend, llm, speech];

  let state: ServiceState = "ok";
  let text = "Tudo pronto";
  if (states.includes("checking")) {
    state = "checking";
    text = "Verificando…";
  } else if (backend === "down") {
    state = "down";
    text = "Backend desconectado";
  } else if (llm === "down") {
    state = "down";
    text = "Ollama não responde";
  } else if (llm === "warning") {
    state = "warning";
    text = `Modelo ${details?.llm.selected_model ?? ""} ausente`;
  } else if (speech !== "ok") {
    state = "warning";
    text = "Voz indisponível";
  }

  const dot: Record<ServiceState, string> = {
    ok: "bg-ios-green",
    warning: "bg-ios-orange",
    down: "bg-ios-red",
    checking: "bg-slate-500 animate-pulse",
  };

  return (
    <NavLink
      to="/configuracoes"
      title="Ver diagnóstico"
      className="flex items-center gap-2.5 rounded-[10px] px-3 py-1.5 text-[12px] text-slate-400 transition hover:bg-white/[0.05] hover:text-slate-200"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot[state]}`} aria-hidden />
      <span className="truncate">{text}</span>
    </NavLink>
  );
}
