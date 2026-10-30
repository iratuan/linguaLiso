import { describe, expect, it } from "vitest";
import { niceScale, smoothPath } from "./charts";

describe("niceScale", () => {
  it("usa marcos redondos entre 0 e 100", () => {
    expect(niceScale(0, 100).ticks).toEqual([0, 25, 50, 75, 100]);
  });

  it("nunca produz marcos fracionários para contagens", () => {
    const scale = niceScale(0, 1, 4, true);
    expect(scale.ticks.every(Number.isInteger)).toBe(true);
    expect(scale.hi).toBeGreaterThanOrEqual(1);
  });

  it("cobre todo o intervalo de dados", () => {
    const scale = niceScale(3, 47);
    expect(scale.lo).toBeLessThanOrEqual(3);
    expect(scale.hi).toBeGreaterThanOrEqual(47);
  });

  it("aceita intervalo degenerado sem dividir por zero", () => {
    const scale = niceScale(5, 5);
    expect(scale.ticks.length).toBeGreaterThan(1);
  });
});

describe("smoothPath", () => {
  it("retorna vazio sem pontos e um ponto isolado sem curva", () => {
    expect(smoothPath([])).toBe("");
    expect(smoothPath([{ x: 1, y: 2 }])).toBe("M1,2");
  });

  it("não ultrapassa os valores dos pontos vizinhos (sem overshoot)", () => {
    const pts = [
      { x: 0, y: 100 },
      { x: 10, y: 100 },
      { x: 20, y: 40 },
      { x: 30, y: 40 },
    ];
    const curve = smoothPath(pts);
    const ys = [...curve.matchAll(/,(-?[\d.]+)/g)].map((m) => Number(m[1]));
    for (const y of ys) {
      expect(y).toBeGreaterThanOrEqual(40 - 1e-9);
      expect(y).toBeLessThanOrEqual(100 + 1e-9);
    }
  });
});
