import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MathText } from "../components/MathText";

describe("MathText", () => {
  it("renders caret exponents as real superscripts", () => {
    const { container } = render(<MathText>{"2^5 grows fast"}</MathText>);
    const sup = container.querySelector("sup");
    expect(sup).not.toBeNull();
    expect(sup?.textContent).toBe("5");
    expect(container.textContent).toBe("25 grows fast");
  });

  it("renders braced caret exponents", () => {
    const { container } = render(<MathText>{"x^{10}"}</MathText>);
    expect(container.querySelector("sup")?.textContent).toBe("10");
  });

  it("renders inline LaTeX with KaTeX", () => {
    const { container } = render(
      <MathText>{"Recall $\\frac{1}{2}$ here"}</MathText>,
    );
    // KaTeX emits a .katex wrapper for rendered math.
    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("falls back to source text on invalid LaTeX instead of throwing", () => {
    expect(() =>
      render(<MathText>{"broken $\\frac{1$ math"}</MathText>),
    ).not.toThrow();
  });

  it("passes plain prose through unchanged", () => {
    const { container } = render(
      <MathText>{"Check the sign when you move -5 across."}</MathText>,
    );
    expect(container.textContent).toBe("Check the sign when you move -5 across.");
    expect(container.querySelector("sup")).toBeNull();
  });

  it("leaves unicode superscripts intact", () => {
    const { container } = render(<MathText>{"Simplify 2³ × 2²"}</MathText>);
    expect(container.textContent).toBe("Simplify 2³ × 2²");
  });
});
