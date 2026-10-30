import { useCallback, useEffect, useRef, useState } from "react";
import { api, describeError } from "../lib/api";
import { type ActiveRecording, type PlaybackHandle, playWav, startRecording, MicrophoneError } from "../lib/audio";

export type RecorderState = "idle" | "recording" | "transcribing";
export type PlaybackState = "idle" | "generating" | "playing";

export const MAX_RECORDING_MS = 60_000;

export interface VoiceOptions {
  voice?: string;
  rate: number;
  volume: number;
}

/** Atualiza o nível e o tempo da gravação sem renderizar a cada quadro. */
const TICK_MS = 200;

/**
 * Gravação do microfone e envio ao backend para transcrição.
 * - `level`: volume atual (0–1), para o medidor.
 * - `elapsedMs`: tempo gravado.
 * - Para sozinha após uma pausa depois da fala, ou no limite de MAX_RECORDING_MS.
 */
/** Depois que a fala começou, este tempo sem voz encerra a gravação e a mensagem é enviada. */
export const SILENCE_END_MS = 10_000;

/** `bySilence` indica que a gravação terminou sozinha por silêncio (o aluno terminou de falar). */
export type TranscriptMeta = { bySilence: boolean };

export function useRecorder(
  onTranscript: (text: string, meta: TranscriptMeta) => void,
  onError: (message: string) => void,
) {
  const [state, setState] = useState<RecorderState>("idle");
  const [micError, setMicError] = useState<MicrophoneError | null>(null);
  const [level, setLevel] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const active = useRef<ActiveRecording | null>(null);
  // Trava: enquanto o microfone está sendo aberto, o botão não pode iniciar outra gravação.
  const starting = useRef(false);
  // Pedido de parada feito durante a abertura do microfone: para assim que ele estiver pronto.
  const stopRequested = useRef(false);
  const autoStop = useRef<number | null>(null);
  const timer = useRef<number | null>(null);
  const callbacks = useRef({ onTranscript, onError });
  callbacks.current = { onTranscript, onError };

  const clearTimers = useCallback(() => {
    if (autoStop.current !== null) window.clearTimeout(autoStop.current);
    if (timer.current !== null) window.clearInterval(timer.current);
    autoStop.current = null;
    timer.current = null;
  }, []);

  const finish = useCallback(
    async (bySilence = false) => {
      if (!active.current) return;
      clearTimers();
      setLevel(0);
      const recording = active.current;
      active.current = null;
      setState("transcribing");
      try {
        const blob = await recording.stop();
        if (blob.size === 0) {
          callbacks.current.onError("Não captei nenhum áudio. Verifique o microfone e tente de novo.");
          return;
        }
        const result = await api.transcribe(blob);
        if (result.empty || !result.text.trim()) {
          callbacks.current.onError("Não consegui entender a gravação. Fale mais perto do microfone.");
          return;
        }
        callbacks.current.onTranscript(result.text.trim(), { bySilence });
      } catch (error) {
        callbacks.current.onError(describeError(error));
      } finally {
        setState("idle");
      }
    },
    [clearTimers],
  );

  const start = useCallback(async () => {
    if (active.current || starting.current) return;
    starting.current = true;
    stopRequested.current = false;
    try {
      setMicError(null);
      const recording = await startRecording({
        onLevel: (value) => setLevel(value),
        onSilence: () => void finish(true),
        silenceMs: SILENCE_END_MS,
      });
      active.current = recording;
      starting.current = false;
      setState("recording");
      setElapsedMs(0);
      const began = Date.now();
      timer.current = window.setInterval(() => setElapsedMs(Date.now() - began), TICK_MS);
      autoStop.current = window.setTimeout(() => void finish(), MAX_RECORDING_MS);
      // O usuário apertou parar enquanto o microfone abria: encerra logo que estiver gravando.
      if (stopRequested.current) void finish();
    } catch (error) {
      starting.current = false;
      const mic = error instanceof MicrophoneError ? error : null;
      setMicError(mic);
      callbacks.current.onError(describeError(error));
    }
  }, [finish]);

  const toggle = useCallback(() => {
    if (active.current) void finish();
    else if (starting.current) stopRequested.current = true;
    else void start();
  }, [finish, start]);

  useEffect(
    () => () => {
      clearTimers();
      active.current?.cancel();
    },
    [clearTimers],
  );

  return { state, micError, level, elapsedMs, toggle };
}

/** Geração e reprodução de voz. Permite interromper a reprodução imediatamente. */
export function usePlayback(options: VoiceOptions, onError: (message: string) => void) {
  const [state, setState] = useState<PlaybackState>("idle");
  const handle = useRef<PlaybackHandle | null>(null);
  const token = useRef(0);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const stop = useCallback(() => {
    token.current += 1; // invalida gerações em andamento
    handle.current?.stop();
    handle.current = null;
    setState("idle");
  }, []);

  const speak = useCallback(
    async (text: string) => {
      stop();
      const current = ++token.current;
      setState("generating");
      try {
        const blob = await api.synthesize(text, optionsRef.current.rate, optionsRef.current.volume);
        if (current !== token.current) return;
        const playing = playWav(blob, { rate: 1, volume: optionsRef.current.volume });
        handle.current = playing;
        setState("playing");
        await playing.finished;
        if (current === token.current) {
          handle.current = null;
          setState("idle");
        }
      } catch (error) {
        if (current !== token.current) return;
        setState("idle");
        onError(describeError(error));
      }
    },
    [stop, onError],
  );

  useEffect(
    () => () => {
      token.current += 1;
      handle.current?.stop();
    },
    [],
  );

  return { state, speak, stop };
}
