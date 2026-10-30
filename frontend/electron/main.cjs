// Processo principal do Electron.
//
// Responsabilidades:
//  - Iniciar o backend (porta 8000) e o servidor de voz (porta 8001) quando não estiverem rodando.
//  - Criar a janela com isolamento de contexto e sem acesso direto ao Node no renderer.
//  - Liberar o microfone somente para a própria aplicação.
//  - Encerrar os processos filhos ao fechar o aplicativo.
//
// Nada aqui chama serviços de internet. Os logs ficam em %APPDATA%/<app>/logs.

const { app, BrowserWindow, ipcMain, session, shell, dialog } = require("electron");

// Nome fixo: define a pasta de dados do usuário (%APPDATA%) independentemente do nome do pacote.
// Não trocar: mudar este nome muda a pasta de dados e a preparação inicial rodaria de novo.
app.setName("English Teacher Local");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const BACKEND_URL = process.env.ETL_BACKEND_URL || "http://127.0.0.1:8000";
const SPEECH_URL = process.env.ETL_SPEECH_URL || "http://127.0.0.1:8001";
const DEV_URL = process.env.ETL_DEV_URL || "http://127.0.0.1:5173";
const BACKEND_HEALTH = `${BACKEND_URL}/api/health`;
const SPEECH_HEALTH = `${SPEECH_URL}/health`;
const STARTUP_TIMEOUT_MS = 60_000;

const children = [];
let logDir = null;

function ensureLogDir() {
  if (!logDir) {
    logDir = path.join(app.getPath("userData"), "logs");
    fs.mkdirSync(logDir, { recursive: true });
  }
  return logDir;
}

/** Pasta com backend e ai-model: no pacote instalado fica em resources/; em desenvolvimento, na raiz do projeto. */
const RUNTIME_ROOT = app.isPackaged ? process.resourcesPath : PROJECT_ROOT;

function pythonFor(folder) {
  // No instalador, o Python embutido e as bibliotecas vêm junto (resources/runtime).
  if (app.isPackaged) return path.join(process.resourcesPath, "runtime", "python.exe");
  const venvPython = path.join(PROJECT_ROOT, folder, ".venv", "Scripts", "python.exe");
  return fs.existsSync(venvPython) ? venvPython : process.env.ETL_PYTHON || "python";
}

/** Dados do usuário ficam fora da pasta do programa (que é somente leitura após a instalação). */
function userDataDir() {
  return app.getPath("userData");
}

function readMachineProfile() {
  try {
    return JSON.parse(fs.readFileSync(path.join(userDataDir(), "perfil-maquina.json"), "utf8"));
  } catch {
    return null;
  }
}

/** Variáveis extras só no app instalado: pasta de dados gravável e modelo escolhido para esta máquina. */
function packagedEnv() {
  if (!app.isPackaged) return {};
  const env = { ETL_DATA_DIR: path.join(userDataDir(), "data") };
  const profile = readMachineProfile();
  if (profile && profile.llm_model) env.ETL_DEFAULT_LLM_MODEL = profile.llm_model;
  return env;
}

/** Primeira execução do instalado: prepara o Ollama e o modelo de linguagem (com confirmação na janela). */
function setupDone() {
  return fs.existsSync(path.join(userDataDir(), "instalacao-concluida.json"));
}

function runFirstRunSetup() {
  return new Promise((resolve) => {
    const script = path.join(process.resourcesPath, "scripts", "preparar.ps1");
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-DataDir", userDataDir()],
      { stdio: "inherit", windowsHide: false }
    );
    child.on("error", () => resolve(1));
    child.on("exit", (code) => resolve(code ?? 1));
  });
}

function isReachable(healthUrl) {
  return new Promise((resolve) => {
    const req = http.get(healthUrl, { timeout: 1500 }, (res) => {
      res.resume();
      resolve(res.statusCode !== undefined && res.statusCode < 500);
    });
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
    req.on("error", () => resolve(false));
  });
}

async function waitFor(healthUrl, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isReachable(healthUrl)) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startService(name, cwd, args, env) {
  const logFile = path.join(ensureLogDir(), `${name}.log`);
  const out = fs.openSync(logFile, "a");
  const child = spawn(pythonFor(path.basename(cwd)), args, {
    cwd,
    env: { ...process.env, ...packagedEnv(), ...env, PYTHONUNBUFFERED: "1" },
    windowsHide: true,
    stdio: ["ignore", out, out],
  });
  child.on("exit", (code) => console.log(`[${name}] encerrado com código ${code}`));
  children.push(child);
  return child;
}

async function ensureServices() {
  const failures = [];

  if (!(await isReachable(BACKEND_HEALTH))) {
    startService(
      "backend",
      path.join(RUNTIME_ROOT, "backend"),
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      {}
    );
  }
  if (!(await isReachable(SPEECH_HEALTH))) {
    startService(
      "speech",
      path.join(RUNTIME_ROOT, "ai-model"),
      ["-m", "uvicorn", "speech_server:app", "--host", "127.0.0.1", "--port", "8001"],
      {}
    );
  }

  const [backendOk, speechOk] = await Promise.all([
    waitFor(BACKEND_HEALTH, STARTUP_TIMEOUT_MS),
    waitFor(SPEECH_HEALTH, STARTUP_TIMEOUT_MS),
  ]);
  if (!backendOk) failures.push(`Backend não iniciou. Veja ${path.join(ensureLogDir(), "backend.log")}`);
  if (!speechOk) failures.push(`Servidor de voz não iniciou. Veja ${path.join(ensureLogDir(), "speech.log")}`);
  return failures;
}

function hardenSession() {
  const ses = session.defaultSession;

  // Só o próprio app pode pedir microfone; qualquer outra permissão é negada.
  ses.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === "media");
  });
  ses.setPermissionCheckHandler((_wc, permission) => permission === "media");

  // Política de conteúdo apenas para o build empacotado (no dev o Vite precisa de inline/eval).
  if (app.isPackaged) {
    ses.webRequest.onHeadersReceived((details, callback) => {
      const csp =
        "default-src 'self'; " +
        `connect-src 'self' ${BACKEND_URL} blob:; ` +
        "media-src 'self' blob:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'";
      callback({
        responseHeaders: { ...details.responseHeaders, "Content-Security-Policy": [csp] },
      });
    });
  }
}

let mainWindow = null;
let chatWindow = null;
let splashWindow = null;

// Ícone do app (janela, barra de tarefas) gerado a partir do logo.
const ICON_PATH = path.join(__dirname, "assets", "icon.ico");

/** Splash com o logo enquanto os serviços sobem. Fecha quando a janela principal estiver pronta. */
function showSplash() {
  splashWindow = new BrowserWindow({
    width: 440,
    height: 560,
    frame: false,
    resizable: false,
    maximizable: false,
    minimizable: false,
    alwaysOnTop: true,
    backgroundColor: "#0b0b0f",
    icon: ICON_PATH,
    show: true,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });
  splashWindow.loadFile(path.join(__dirname, "splash.html"));
  splashWindow.center();
}

function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  splashWindow = null;
}

/** Carrega a aplicação numa rota (ex.: "/chat-window"), em desenvolvimento ou empacotada. */
function loadRoute(win, route) {
  if (app.isPackaged) {
    win.loadFile(path.join(PROJECT_ROOT, "frontend", "dist", "index.html"), { hash: route });
  } else {
    win.loadURL(`${DEV_URL}/#${route}`);
  }
}

/** Janela do professor: pequena, sempre no topo, por cima de outros programas. */
function openChatWindow() {
  if (chatWindow && !chatWindow.isDestroyed()) {
    chatWindow.show();
    chatWindow.focus();
    return;
  }
  chatWindow = new BrowserWindow({
    width: 400,
    height: 600,
    minWidth: 330,
    minHeight: 380,
    title: "Professor",
    backgroundColor: "#0b0b0f",
    autoHideMenuBar: true,
    alwaysOnTop: true,
    // Barra de título integrada, como na janela principal, com o vidro nativo do Windows por trás.
    titleBarStyle: "hidden",
    titleBarOverlay: { color: "#0b0b0f", symbolColor: "#cbd5e1", height: 36 },
    ...(process.platform === "win32" ? { backgroundMaterial: "acrylic" } : {}),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });
  chatWindow.setAlwaysOnTop(true, "floating");
  chatWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  chatWindow.webContents.on("will-navigate", (event, url) => {
    const allowed = url.startsWith("file://") || url.startsWith(DEV_URL);
    if (!allowed) event.preventDefault();
  });
  loadRoute(chatWindow, "/chat-window");
  // Fechar a janela do chat devolve a aplicação principal.
  chatWindow.on("closed", () => {
    chatWindow = null;
    restoreMainWindow();
  });
  mainWindow?.minimize();
}

/** Fecha a janela do chat e traz a aplicação principal de volta. */
function restoreMainWindow() {
  if (chatWindow && !chatWindow.isDestroyed()) chatWindow.close();
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
}

// Só estes dois canais existem; o renderer não ganha acesso a nada além disso.
ipcMain.handle("chat:popout", () => openChatWindow());
ipcMain.handle("chat:restore", () => restoreMainWindow());

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 640,
    title: "English Teacher Local",
    icon: ICON_PATH,
    backgroundColor: "#0b0b0f",
    autoHideMenuBar: true,
    // Só aparece quando estiver pronta, para o splash cobrir a espera.
    show: false,
    // Barra de título integrada ao tema: o conteúdo ocupa a faixa do topo, e os
    // controles nativos (minimizar, maximizar, fechar) ficam sobre ela.
    titleBarStyle: "hidden",
    titleBarOverlay: { color: "#0b0b0f", symbolColor: "#cbd5e1", height: 36 },
    // Windows 11: material Acrílico (vidro translúcido que deixa ver o que está atrás da janela).
    // Em versões antigas do Windows o Electron ignora a opção e a janela segue opaca.
    ...(process.platform === "win32" ? { backgroundMaterial: "acrylic" } : {}),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });

  // Links externos abrem no navegador padrão; a janela nunca navega para fora.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http://") || url.startsWith("https://")) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    const allowed = url.startsWith("file://") || url.startsWith(DEV_URL);
    if (!allowed) event.preventDefault();
  });

  win.once("ready-to-show", () => {
    closeSplash();
    win.show();
  });
  // Se a página não carregar, não deixa o splash preso: mostra a janela e segue.
  win.webContents.once("did-fail-load", () => {
    closeSplash();
    win.show();
  });
  loadRoute(win, "/");
  mainWindow = win;
  win.on("closed", () => {
    mainWindow = null;
    if (chatWindow && !chatWindow.isDestroyed()) chatWindow.close();
  });
  return win;
}

app.whenReady().then(async () => {
  hardenSession();
  showSplash();

  if (app.isPackaged && !setupDone()) {
    const code = await runFirstRunSetup();
    if (code !== 0) {
      closeSplash();
      dialog.showErrorBox(
        "Preparação não concluída",
        "A instalação do Ollama ou do modelo de linguagem não terminou. O app abre, mas o professor só responde depois da preparação. Abra o app de novo para tentar outra vez."
      );
    }
  }

  const failures = await ensureServices();
  createWindow();

  if (failures.length > 0) {
    closeSplash();
    dialog.showErrorBox(
      "Serviços locais indisponíveis",
      failures.join("\n") +
        "\n\nO aplicativo continua aberto, mas o chat e a voz podem não funcionar. " +
        "Execute scripts\\diagnostico.ps1 para ver o que falta."
    );
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", () => {
  for (const child of children) {
    if (!child.killed) child.kill();
  }
});
