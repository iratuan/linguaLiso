import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CourseLesson } from "../lib/types";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      courseLesson: vi.fn(),
      checkExercise: vi.fn(),
      completeCourseLesson: vi.fn(),
      synthesize: vi.fn(),
      courseExerciseAudio: vi.fn(),
    },
  };
});

import { api } from "../lib/api";
import { LessonPlayerPage } from "./LessonPlayerPage";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const lesson = (answeredCount: number): CourseLesson => ({
  id: "a1-1-1",
  title: "Cumprimentos e o verbo to be",
  objective: "Usar am, is e are.",
  explanation: "Use **to be**.\n\n- I **am**",
  key_phrases: [{ en: "Hello", pt: "Olá" }],
  level: "A1",
  unit_id: "a1-u1",
  position: 1,
  status: "in_progress",
  locked: false,
  score: null,
  pass_score: 70,
  answered: answeredCount,
  can_complete: false,
  next_lesson_id: "a1-1-2",
  exercises: [
    {
      id: "e1",
      type: "multiple_choice",
      prompt: "p1",
      hint: null,
      answered: answeredCount > 0,
      correct: answeredCount > 0 ? true : null,
      last_answer: null,
      options: ["am", "is"],
    },
    {
      id: "e2",
      type: "fill_blank",
      prompt: "p2",
      hint: null,
      answered: answeredCount > 1,
      correct: answeredCount > 1 ? true : null,
      last_answer: "is",
    },
    {
      id: "e3",
      type: "translate",
      prompt: "p3",
      hint: null,
      answered: answeredCount > 2,
      correct: answeredCount > 2 ? true : null,
      last_answer: "I am a student.",
    },
    {
      id: "e4",
      type: "reorder",
      prompt: "Monte a frase: meu nome é Carlos",
      hint: null,
      answered: false,
      correct: null,
      last_answer: null,
      words: ["Carlos", "is", "name", "My"],
    },
  ],
});

let host: HTMLDivElement | null = null;
afterEach(() => {
  host?.remove();
  host = null;
  vi.clearAllMocks();
});

async function flush() {
  await act(async () => {
    await new Promise((r) => setTimeout(r, 30));
  });
}

function mount() {
  host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(
      <MemoryRouter initialEntries={["/trilhas/a1-1-1"]}>
        <Routes>
          <Route path="/trilhas/:lessonId" element={<LessonPlayerPage />} />
        </Routes>
      </MemoryRouter>,
    );
  });
  return root;
}

function clickButton(text: string) {
  const button = [...document.querySelectorAll("button")].find((b) => b.textContent?.trim() === text);
  if (!button) throw new Error(`Botão não encontrado: ${text}`);
  act(() => button.click());
}

describe("LessonPlayerPage resume flow", () => {
  it("opens reorder exercise and accepts word taps", async () => {
    vi.mocked(api.courseLesson).mockResolvedValue(lesson(3));
    mount();
    await flush();
    clickButton("Continuar exercícios");
    await flush();
    expect(document.body.textContent).toContain("Monte a frase");

    clickButton("My");
    await flush();
    const picked = [...document.querySelectorAll("button")].filter((b) => b.className.includes("bg-brand-500"));
    expect(picked.map((b) => b.textContent)).toEqual(["My"]);
    expect(document.body.textContent).toContain("Monte a frase");
  });
});
