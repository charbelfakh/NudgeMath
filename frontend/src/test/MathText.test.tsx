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

  it("tolerates stray spaces in caret exponents (OCR noise)", () => {
    const { container } = render(<MathText>{"(x^ {2 } - 11x + 30)"}</MathText>);
    expect(container.querySelector("sup")?.textContent).toBe("2");
    expect(container.textContent).toBe("(x2 - 11x + 30)");
  });

  it("collapses literal escape sequences to a space", () => {
    // The transcription leaked a literal backslash-n (two visible chars).
    const { container } = render(
      <MathText>{"Solve for x in,\\n(x^{2}-5x+5)"}</MathText>,
    );
    expect(container.textContent).not.toContain("\\n");
    expect(container.textContent).toBe("Solve for x in, (x2-5x+5)");
  });

  it("collapses a literal escape before a capitalized sentence", () => {
    const { container } = render(<MathText>{"Step 1 done.\\nSolve for x."}</MathText>);
    expect(container.textContent).toBe("Step 1 done. Solve for x.");
  });

  it("does not mangle bare LaTeX commands starting with n/r/t in prose", () => {
    // `\times`, `\neq`, `\rho` share a prefix with literal escapes; the escape
    // collapser must leave them intact (not turn `\times` into " imes").
    const { container } = render(<MathText>{"so 3 \\times 4 \\neq 11"}</MathText>);
    expect(container.textContent).toContain("\\times");
    expect(container.textContent).toContain("\\neq");
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
