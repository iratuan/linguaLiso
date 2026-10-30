import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ExerciseCard } from "./ExerciseCard";
import type { CourseExercise } from "../../lib/types";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const reorder: CourseExercise = {
  id: "a1-1-1-e4",
  type: "reorder",
  prompt: "Monte a frase: meu nome é Carlos",
  hint: null,
  answered: false,
  correct: null,
  last_answer: null,
  words: ["Carlos", "is", "name", "My"],
};

let host: HTMLDivElement | null = null;

afterEach(() => {
  host?.remove();
  host = null;
});

function mount(element: React.ReactElement) {
  host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(element));
  return root;
}

const baseProps = {
  index: 3,
  total: 4,
  isLast: true,
  onCheck: vi.fn(async () => ({ correct: true, feedback_pt: null, correct_answer: null, used_ai_check: false })),
  onNext: vi.fn(),
  onListen: vi.fn(),
  listening: false,
  onError: vi.fn(),
};

describe("ExerciseCard (reorder)", () => {
  it("renders the word bank without looping", () => {
    mount(<ExerciseCard {...baseProps} exercise={reorder} />);
    expect(document.body.textContent).toContain("Monte a frase");
    const words = [...document.querySelectorAll("button")].map((b) => b.textContent);
    expect(words).toEqual(expect.arrayContaining(["Carlos", "is", "name", "My"]));
  });

  it("builds the sentence by tapping words", () => {
    mount(<ExerciseCard {...baseProps} exercise={reorder} />);
    const tap = (text: string) =>
      act(() => {
        [...document.querySelectorAll("button")].find((b) => b.textContent === text)?.click();
      });
    tap("My");
    tap("name");
    const picked = [...document.querySelectorAll("button")].filter((b) => b.className.includes("bg-brand-500"));
    expect(picked.map((b) => b.textContent)).toEqual(["My", "name"]);
  });

  it("renders a translate exercise with an input", () => {
    mount(
      <ExerciseCard
        {...baseProps}
        exercise={{ ...reorder, id: "t", type: "translate", prompt: "Eu sou estudante.", words: undefined }}
      />,
    );
    expect(document.querySelector("input")).not.toBeNull();
  });
});

describe("ExerciseCard (open reply)", () => {
  const openReply: CourseExercise = {
    id: "c1",
    type: "open_reply",
    prompt: "Hi! What would you like to order?",
    context: "Você está no balcão de um café.",
    hint: null,
    answered: false,
    correct: null,
    last_answer: null,
  };

  it("mostra a situação, ouvir o professor e o microfone", () => {
    mount(<ExerciseCard {...baseProps} exercise={openReply} />);
    expect(document.body.textContent).toContain("Você está no balcão de um café.");
    expect(document.body.textContent).toContain("Ouvir o professor");
    expect(document.querySelector('button[aria-label="Responder falando"]')).not.toBeNull();
  });

  it("não mostra a situação quando o exercício não tem contexto", () => {
    mount(<ExerciseCard {...baseProps} exercise={{ ...openReply, context: undefined }} />);
    expect(document.body.textContent).not.toContain("Situação:");
  });
});
