import { describe, expect, it } from "vitest";
import { ApiError, describeError } from "./api";
import { describeMicrophoneError, MicrophoneError, pickMimeType } from "./audio";
import { formatDateTime, formatRelativeDue, formatSeconds } from "./format";

describe("pickMimeType", () => {
  it("prefere WebM/Opus quando suportado", () => {
    expect(pickMimeType(() => true)).toBe("audio/webm;codecs=opus");
  });

  it("cai para o próximo formato suportado", () => {
    expect(pickMimeType((t) => t === "audio/mp4")).toBe("audio/mp4");
  });

  it("retorna string vazia quando nada é suportado", () => {
    expect(pickMimeType(() => false)).toBe("");
  });
});

describe("describeMicrophoneError", () => {
  const domError = (name: string) => new DOMException("x", name);

  it("negação de permissão", () => {
    const err = describeMicrophoneError(domError("NotAllowedError"));
    expect(err.code).toBe("permission_denied");
    expect(err.message).toContain("Permissão do microfone negada");
  });

  it("dispositivo ausente", () => {
    expect(describeMicrophoneError(domError("NotFoundError")).code).toBe("no_device");
  });

  it("microfone ocupado", () => {
    expect(describeMicrophoneError(domError("NotReadableError")).code).toBe("busy");
  });

  it("preserva MicrophoneError já criado", () => {
    const original = new MicrophoneError("x", "busy");
    expect(describeMicrophoneError(original)).toBe(original);
  });
});

describe("describeError", () => {
  it("usa a mensagem do ApiError sem alterar", () => {
    expect(describeError(new ApiError("Modelo ausente", 503, "model_missing"))).toBe("Modelo ausente");
  });

  it("traduz falha de rede para orientação ao usuário", () => {
    expect(describeError(new TypeError("Failed to fetch"))).toContain("backend");
  });

  it("trata valores desconhecidos", () => {
    expect(describeError(42)).toBe("Erro inesperado.");
  });
});

describe("format helpers", () => {
  it("formatSeconds", () => {
    expect(formatSeconds(65.9)).toBe("01:05");
  });

  it("formatRelativeDue em horas e dias", () => {
    const now = new Date("2026-10-28T12:00:00Z");
    expect(formatRelativeDue("2026-10-28T10:00:00Z", now)).toBe("Para revisar agora");
    expect(formatRelativeDue("2026-10-28T18:00:00Z", now)).toBe("Revisar em 6 h");
    expect(formatRelativeDue("2026-10-31T12:00:00Z", now)).toBe("Revisar em 3 dia(s)");
  });

  it("formatDateTime devolve o valor original quando inválido", () => {
    expect(formatDateTime("nao-e-data")).toBe("nao-e-data");
  });
});
