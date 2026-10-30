// Captura do microfone e reprodução de áudio no renderer.
// O áudio nunca é salvo em disco pelo app: fica na memória até ser enviado ao backend.

const PREFERRED_MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

/** Escolhe o primeiro formato suportado pelo Chromium/Electron. Retorna "" se nenhum for suportado. */
export function pickMimeType(isSupported: (type: string) => boolean = MediaRecorder.isTypeSupported): string {
  return PREFERRED_MIME_TYPES.find((type) => isSupported(type)) ?? "";
}

export class MicrophoneError extends Error {
  readonly code: "permission_denied" | "no_device" | "unsupported" | "busy";

  constructor(message: string, code: MicrophoneError["code"]) {
    super(message);
    this.name = "MicrophoneError";
    this.code = code;
  }
}

export function describeMicrophoneError(error: unknown): MicrophoneError {
  if (error instanceof MicrophoneError) return error;
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return new MicrophoneError(
      "Permissão do microfone negada. Libere o microfone para o aplicativo.",
      "permission_denied",
    );
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") {
    return new MicrophoneError("Nenhum microfone foi encontrado. Conecte um dispositivo de entrada.", "no_device");
  }
  if (name === "NotReadableError" || name === "AbortError") {
    return new MicrophoneError("O microfone está sendo usado por outro programa.", "busy");
  }
  return new MicrophoneError("Não foi possível acessar o microfone.", "unsupported");
}

export interface ActiveRecording {
  stop: () => Promise<Blob>;
  cancel: () => void;
  startedAt: number;
}

export interface RecordingOptions {
  deviceId?: string;
  /** Nível atual da voz, de 0 a 1, para o medidor da interface. */
  onLevel?: (level: number) => void;
  /** Chamado uma vez quando há fala seguida de silêncio por `silenceMs`. */
  onSilence?: () => void;
  silenceMs?: number;
}

/** Acima deste nível (RMS, 0–1) o áudio é considerado fala. Ambiente silencioso fica bem abaixo. */
const SPEECH_THRESHOLD = 0.035;

/** Inicia a gravação. Lança MicrophoneError se o microfone não puder ser usado. */
export async function startRecording(options: RecordingOptions = {}): Promise<ActiveRecording> {
  if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new MicrophoneError("Este ambiente não suporta gravação de áudio.", "unsupported");
  }

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: options.deviceId ? { deviceId: { exact: options.deviceId } } : true,
    });
  } catch (error) {
    throw describeMicrophoneError(error);
  }

  const mimeType = pickMimeType();
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks: Blob[] = [];
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });

  const meter = startLevelMeter(stream, options);

  const release = () => {
    meter.stop();
    stream.getTracks().forEach((track) => track.stop());
  };
  recorder.start(250);

  return {
    startedAt: Date.now(),
    stop: () =>
      new Promise<Blob>((resolve, reject) => {
        recorder.addEventListener(
          "stop",
          () => {
            release();
            resolve(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
          },
          { once: true },
        );
        recorder.addEventListener(
          "error",
          () => {
            release();
            reject(new MicrophoneError("Falha durante a gravação.", "unsupported"));
          },
          { once: true },
        );
        if (recorder.state !== "inactive") recorder.stop();
        else {
          release();
          resolve(new Blob(chunks, { type: "audio/webm" }));
        }
      }),
    cancel: () => {
      if (recorder.state !== "inactive") recorder.stop();
      release();
    },
  };
}

/**
 * Mede o volume do microfone enquanto grava. Reporta o nível para a tela e avisa quando a fala
 * termina (silêncio por `silenceMs`). Silêncio antes de qualquer fala não dispara nada: quem
 * ainda não começou a falar não é interrompido.
 */
function startLevelMeter(stream: MediaStream, options: RecordingOptions): { stop: () => void } {
  const AudioCtor =
    window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtor) return { stop: () => undefined };

  const context = new AudioCtor();
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);

  const silenceMs = options.silenceMs ?? 1800;
  let frame = 0;
  let heardSpeech = false;
  let lastVoiceAt = performance.now();
  let lastReported = -1;
  let finished = false;

  const tick = () => {
    analyser.getFloatTimeDomainData(samples);
    let sum = 0;
    for (const s of samples) sum += s * s;
    const rms = Math.sqrt(sum / samples.length);
    // Escala logarítmica simples para a barra de nível parecer proporcional à voz.
    const level = Math.min(1, Math.max(0, (Math.log10(rms + 1e-4) + 3) / 2));
    const now = performance.now();

    if (Math.abs(level - lastReported) > 0.02) {
      lastReported = level;
      options.onLevel?.(level);
    }
    if (rms > SPEECH_THRESHOLD) {
      heardSpeech = true;
      lastVoiceAt = now;
    } else if (heardSpeech && !finished && now - lastVoiceAt > silenceMs) {
      finished = true;
      options.onSilence?.();
    }
    frame = window.requestAnimationFrame(tick);
  };
  frame = window.requestAnimationFrame(tick);

  let closed = false;
  return {
    stop: () => {
      if (closed) return;
      closed = true;
      window.cancelAnimationFrame(frame);
      source.disconnect();
      void context.close().catch(() => undefined);
    },
  };
}

export interface PlaybackHandle {
  stop: () => void;
  finished: Promise<void>;
}

/** Toca um WAV e devolve um handle para interromper a reprodução imediatamente. */
export function playWav(blob: Blob, options: { rate?: number; volume?: number } = {}): PlaybackHandle {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.playbackRate = options.rate ?? 1;
  audio.volume = Math.min(1, Math.max(0, options.volume ?? 1));

  let release: () => void = () => undefined;
  const finished = new Promise<void>((resolve) => {
    release = () => {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.addEventListener("ended", () => release(), { once: true });
    audio.addEventListener("error", () => release(), { once: true });
  });

  void audio.play().catch(() => release());
  return { stop: () => release(), finished };
}
