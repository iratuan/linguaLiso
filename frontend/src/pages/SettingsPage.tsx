import { useEffect, useState } from "react";
import { Download, RefreshCw, Trash2 } from "lucide-react";
import { api, describeError } from "../lib/api";
import { LEVEL_LABELS } from "../lib/format";
import { THEME_LABELS, applyAppearance, type AppTheme } from "../lib/appearance";
import {
  PERSONA_DESCRIPTIONS,
  PERSONA_LABELS,
  type Diagnostics,
  type Level,
  type Profile,
  type Settings,
  type TeacherPersona,
} from "../lib/types";
import {
  ErrorBanner,
  PageContainer,
  PageHeader,
  Segmented,
  SettingRow,
  SettingsGroup,
  Slider,
  Switch,
} from "../components/ui";

const CONFIRM_TEXT = "APAGAR MEUS DADOS";
const EMPTY_PROFILE: Profile = {
  display_name: "",
  level: "A1",
  english_variant: "american",
  explanation_language: "pt-BR",
  study_minutes_goal: 20,
};

export function SettingsPage() {
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [savedProfile, setSavedProfile] = useState<Profile | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [checking, setChecking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedSettings, setSavedSettings] = useState<Settings | null>(null);

  const refreshDiagnostics = () => {
    setChecking(true);
    api
      .diagnostics()
      .then(setDiagnostics)
      .catch((e) => setError(describeError(e)))
      .finally(() => setChecking(false));
  };

  useEffect(() => {
    Promise.all([api.getProfile(), api.getSettings()])
      .then(([p, s]) => {
        if (p) {
          setProfile(p);
          setSavedProfile(p);
        }
        setSettings(s);
        setSavedSettings(s);
      })
      .catch((e) => setError(describeError(e)));
    refreshDiagnostics();
  }, []);

  const flash = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(null), 2600);
  };

  // Alterações ficam como rascunho até o botão "Salvar alterações" (ou são descartadas).
  const changeSetting = (changes: Partial<Settings>) => setSettings((s) => (s ? { ...s, ...changes } : s));
  const slide = changeSetting;
  const changeProfile = (next: Profile) => setProfile(next);

  const profileChanged = JSON.stringify(profile) !== JSON.stringify(savedProfile ?? EMPTY_PROFILE);
  const changedSettings = (): Partial<Settings> => {
    if (!settings || !savedSettings) return {};
    const changes: Record<string, unknown> = {};
    for (const key of Object.keys(settings) as (keyof Settings)[]) {
      if (JSON.stringify(settings[key]) !== JSON.stringify(savedSettings[key])) changes[key] = settings[key];
    }
    return changes as Partial<Settings>;
  };
  const settingsChanged = Object.keys(changedSettings()).length > 0;
  const dirty = profileChanged || settingsChanged;

  const saveAll = async () => {
    setError(null);
    setSaving(true);
    try {
      if (settingsChanged) {
        const updated = await api.updateSettings(changedSettings());
        setSettings(updated);
        setSavedSettings(updated);
      }
      if (profileChanged) {
        const saved = await api.saveProfile(profile);
        setProfile(saved);
        setSavedProfile(saved);
      }
      flash("Alterações salvas");
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSaving(false);
    }
  };

  const discardAll = () => {
    setProfile(savedProfile ?? EMPTY_PROFILE);
    if (savedSettings) setSettings(savedSettings);
  };

  const deleteData = async () => {
    setError(null);
    try {
      await api.deleteData(confirmText);
      setProfile(EMPTY_PROFILE);
      setSavedProfile(null);
      setConfirmText("");
      flash("Dados do aluno apagados. Preferências mantidas");
    } catch (e) {
      setError(describeError(e));
    }
  };

  const modelOptions = settings ? [...new Set([settings.llm_model_default, settings.llm_model_fallback])] : [];

  return (
    <div className="flex-1 overflow-y-auto">
      <PageContainer>
        <PageHeader path="/configuracoes" title="Ajustes" subtitle="Tudo fica salvo neste computador." />
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        {notice && (
          <div className="animate-rise fixed right-8 top-8 z-50 rounded-full border border-line bg-surface-2/90 px-4 py-2 text-[13px] text-slate-100 shadow-xl backdrop-blur-2xl">
            {notice}
          </div>
        )}

        <div className="flex flex-col gap-10">
          {/* ----- Perfil ----- */}
          <SettingsGroup
            title="Perfil"
            footer="O nível define a dificuldade das conversas e das trilhas. Você pode ajustá-lo a qualquer momento."
          >
            <SettingRow
              label="Nome"
              htmlFor="p-name"
              control={
                <input
                  id="p-name"
                  className="w-56 bg-transparent text-right text-[15px] text-slate-100 placeholder:text-slate-600 focus:outline-none"
                  value={profile.display_name}
                  placeholder="Como o professor te chama"
                  maxLength={80}
                  onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
                />
              }
            />
            <SettingRow
              label="Nível"
              htmlFor="p-level"
              control={
                <select
                  id="p-level"
                  className="cursor-pointer bg-transparent text-right text-[15px] text-brand-300 focus:outline-none [&>option]:bg-surface-2"
                  value={profile.level}
                  onChange={(e) => changeProfile({ ...profile, level: e.target.value as Level })}
                >
                  {(Object.keys(LEVEL_LABELS) as Level[]).map((l) => (
                    <option key={l} value={l}>
                      {LEVEL_LABELS[l]}
                    </option>
                  ))}
                </select>
              }
            />
            <SettingRow
              label="Inglês"
              description="Sotaque e grafia usados pelo professor"
              control={
                <Segmented
                  label="Variante do inglês"
                  value={profile.english_variant}
                  onChange={(v) => changeProfile({ ...profile, english_variant: v })}
                  options={[
                    { value: "american", label: "Americano" },
                    { value: "british", label: "Britânico" },
                  ]}
                />
              }
            />
            <SettingRow
              label="Meta diária"
              description="Minutos de estudo por dia"
              control={
                <div className="flex items-center gap-2 text-[15px] text-slate-100">
                  <input
                    id="p-goal"
                    type="number"
                    min={5}
                    max={240}
                    aria-label="Meta diária em minutos"
                    className="w-16 rounded-lg bg-white/[0.06] px-2 py-1 text-right focus:outline-none focus:ring-1 focus:ring-brand-500"
                    value={profile.study_minutes_goal}
                    onChange={(e) => setProfile({ ...profile, study_minutes_goal: Number(e.target.value) })}
                  />
                  <span className="text-slate-500">min</span>
                </div>
              }
            />
          </SettingsGroup>

          {/* ----- Conversa ----- */}
          <SettingsGroup title="Conversa" footer="Modelos precisam estar instalados no Ollama (ollama pull).">
            {settings && (
              <>
                <SettingRow
                  label="Idioma que você estuda"
                  description="Trilha, conversas e reconhecimento de voz usam este idioma"
                  control={
                    <Segmented
                      label="Idioma que você estuda"
                      value={settings.target_language}
                      onChange={(v) => void changeSetting({ target_language: v })}
                      options={[
                        { value: "en", label: "Inglês" },
                        { value: "fr", label: "Francês" },
                      ]}
                    />
                  }
                />
                <SettingRow
                  label="Personalidade do professor"
                  description={PERSONA_DESCRIPTIONS[settings.teacher_persona]}
                  control={
                    <Segmented
                      label="Personalidade do professor"
                      value={settings.teacher_persona}
                      onChange={(v) => void changeSetting({ teacher_persona: v })}
                      options={(Object.keys(PERSONA_LABELS) as TeacherPersona[]).map((p) => ({
                        value: p,
                        label: PERSONA_LABELS[p],
                      }))}
                    />
                  }
                />
                <SettingRow
                  label="Modelo"
                  control={
                    <select
                      aria-label="Modelo de linguagem"
                      className="cursor-pointer bg-transparent text-right text-[15px] text-brand-300 focus:outline-none [&>option]:bg-surface-2"
                      value={settings.llm_model ?? settings.llm_model_default}
                      onChange={(e) => void changeSetting({ llm_model: e.target.value })}
                    >
                      {modelOptions.map((m) => (
                        <option key={m} value={m}>
                          {m}
                          {m === settings.llm_model_default ? " (padrão)" : " (leve)"}
                        </option>
                      ))}
                    </select>
                  }
                />
                <SettingRow
                  label="Criatividade"
                  description={`Temperatura ${settings.llm_temperature.toFixed(1)}. Valores baixos são mais previsíveis.`}
                  control={
                    <Slider
                      label="Criatividade"
                      min={0}
                      max={1.5}
                      step={0.1}
                      value={settings.llm_temperature}
                      onChange={(v) => slide({ llm_temperature: v })}
                    />
                  }
                />
                <SettingRow
                  label="Memória da conversa"
                  description={`Últimas ${settings.history_limit} mensagens enviadas ao professor`}
                  control={
                    <Slider
                      label="Memória da conversa"
                      min={2}
                      max={40}
                      step={1}
                      value={settings.history_limit}
                      onChange={(v) => slide({ history_limit: v })}
                    />
                  }
                />
              </>
            )}
          </SettingsGroup>

          {/* ----- Aparência ----- */}
          {settings && (
            <SettingsGroup
              title="Aparência"
              footer="Quanto maior a transparência, mais o fundo da janela aparece. No Windows, a janela deixa ver o que está atrás dela."
            >
              <SettingRow
                label="Transparência"
                description="Prévia imediata. Salve para manter."
                control={
                  <Slider
                    label="Transparência da interface"
                    min={0}
                    max={80}
                    step={5}
                    value={settings.ui_transparency}
                    onChange={(v) => {
                      applyAppearance({ transparency: v, theme: settings.app_theme });
                      slide({ ui_transparency: v });
                    }}
                  />
                }
              />
              <SettingRow
                label="Tema"
                description="Papel: fundo creme e fonte serifada, como um leitor digital."
                control={
                  <Segmented
                    label="Tema"
                    value={settings.app_theme}
                    onChange={(v: AppTheme) => {
                      applyAppearance({ transparency: settings.ui_transparency, theme: v });
                      slide({ app_theme: v });
                    }}
                    options={(Object.keys(THEME_LABELS) as AppTheme[]).map((t) => ({
                      value: t,
                      label: THEME_LABELS[t],
                    }))}
                  />
                }
              />
            </SettingsGroup>
          )}

          {/* ----- Voz ----- */}
          {settings && (
            <SettingsGroup title="Voz" footer="A voz é gerada no seu computador. Nada é enviado para a internet.">
              <SettingRow
                label="Resposta do professor"
                description="Falar as respostas em voz alta ou mostrar só texto"
                control={
                  <Segmented
                    label="Resposta do professor"
                    value={settings.response_mode}
                    onChange={(v) => void changeSetting({ response_mode: v })}
                    options={[
                      { value: "audio", label: "Voz" },
                      { value: "text", label: "Texto" },
                    ]}
                  />
                }
              />
              <SettingRow
                label="Revisar antes de enviar"
                description="Mostra o que foi reconhecido para você conferir"
                control={
                  <Switch
                    label="Revisar transcrição antes de enviar"
                    checked={settings.confirm_transcription}
                    onChange={(v) => void changeSetting({ confirm_transcription: v })}
                  />
                }
              />
              <SettingRow
                label="Velocidade"
                description={`${settings.speech_rate.toFixed(2)}×`}
                control={
                  <Slider
                    label="Velocidade da voz"
                    min={0.5}
                    max={1.5}
                    step={0.05}
                    value={settings.speech_rate}
                    onChange={(v) => slide({ speech_rate: v })}
                  />
                }
              />
              <SettingRow
                label="Volume"
                description={`${Math.round(settings.speech_volume * 100)}%`}
                control={
                  <Slider
                    label="Volume da voz"
                    min={0}
                    max={1}
                    step={0.05}
                    value={settings.speech_volume}
                    onChange={(v) => slide({ speech_volume: v })}
                  />
                }
              />
            </SettingsGroup>
          )}

          {/* ----- Diagnóstico ----- */}
          <SettingsGroup
            title="Diagnóstico"
            footer={diagnostics ? `Espaço livre em disco: ${diagnostics.disk_free_gb} GB` : undefined}
          >
            {diagnostics ? (
              <>
                <DiagRow
                  ok={diagnostics.backend.schema_version > 0}
                  label="Banco de dados"
                  detail={diagnostics.database.path}
                />
                <DiagRow
                  ok={diagnostics.llm.reachable && diagnostics.llm.model_installed}
                  label={`Modelo ${diagnostics.llm.selected_model}`}
                  detail={diagnostics.llm.message}
                />
                <DiagRow
                  ok={diagnostics.speech.stt_ready}
                  label="Reconhecimento de fala"
                  detail={diagnostics.speech.message}
                />
                <DiagRow
                  ok={diagnostics.speech.tts_ready}
                  label="Voz do professor"
                  detail={diagnostics.speech.message}
                />
              </>
            ) : (
              <SettingRow label="Verificando componentes…" control={null} />
            )}
            <div className="flex justify-end px-4 py-3">
              <button
                type="button"
                className="btn-ghost !py-1.5 text-[13px]"
                onClick={refreshDiagnostics}
                disabled={checking}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} /> Verificar novamente
              </button>
            </div>
          </SettingsGroup>

          {/* ----- Privacidade ----- */}
          <SettingsGroup
            title="Seus dados"
            footer="A exportação gera um arquivo JSON aberto, legível em qualquer editor de texto."
          >
            <SettingRow
              label="Exportar histórico"
              description="Perfil, conversas, correções, aulas e vocabulário"
              control={
                <a className="btn-ghost !py-1.5 text-[13px]" href={api.exportUrl()} download>
                  <Download className="h-3.5 w-3.5" /> Exportar
                </a>
              }
            />
            <div className="flex flex-col gap-3 px-4 py-4">
              <div>
                <p className="text-[15px] text-rose-200">Apagar dados do aluno</p>
                <p className="mt-0.5 text-[13px] text-slate-500">
                  Remove perfil, conversas, correções, progresso e vocabulário. Suas preferências são mantidas. Não pode
                  ser desfeito.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <input
                  aria-label={`Digite ${CONFIRM_TEXT} para confirmar`}
                  placeholder={CONFIRM_TEXT}
                  className="field w-full max-w-xs !py-2 text-[14px]"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                />
                <button
                  type="button"
                  className="btn-danger !py-2 text-[14px]"
                  disabled={confirmText !== CONFIRM_TEXT}
                  onClick={() => void deleteData()}
                >
                  <Trash2 className="h-3.5 w-3.5" /> Apagar
                </button>
              </div>
            </div>
          </SettingsGroup>
        </div>
      </PageContainer>

      {dirty && (
        <div className="animate-rise fixed bottom-6 right-8 z-40 flex items-center gap-3 rounded-full border border-line bg-surface-2/95 py-2 pl-5 pr-2 shadow-2xl backdrop-blur-2xl">
          <span className="text-[14px] text-slate-300">Alterações não salvas</span>
          <button type="button" className="btn-ghost !py-2" onClick={discardAll} disabled={saving}>
            Descartar
          </button>
          <button type="button" className="btn-primary !py-2" onClick={() => void saveAll()} disabled={saving}>
            {saving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      )}
    </div>
  );
}

function DiagRow({ ok, label, detail }: { ok: boolean; label: string; detail?: string }) {
  return (
    <div className="flex items-center justify-between gap-6 px-4 py-3">
      <div className="min-w-0">
        <p className="text-[15px] text-slate-100">{label}</p>
        {detail && <p className="mt-0.5 truncate text-[13px] text-slate-500">{detail}</p>}
      </div>
      <span className={`flex shrink-0 items-center gap-1.5 text-[13px] ${ok ? "text-ios-green" : "text-ios-red"}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-ios-green" : "bg-ios-red"}`} />
        {ok ? "OK" : "Atenção"}
      </span>
    </div>
  );
}
