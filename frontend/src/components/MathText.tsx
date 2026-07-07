import { useMemo, type ReactNode } from "react";
import katex from "katex";

/**
 * Render mixed prose + math accurately.
 *
 * - LaTeX inside `$$…$$`, `\[…\]` (display) or `$…$`, `\(…\)` (inline) is rendered with
 *   KaTeX. Invalid LaTeX falls back to its source text instead of throwing.
 * - Outside delimiters, caret exponents (`2^5`, `x^{10}`, `2^{3+2}`) become real
 *   superscripts. Unicode math (`2³`, `×`, `÷`, `≤`) already displays correctly and is
 *   passed through untouched.
 *
 * This covers both the seed problems (plain arithmetic) and LLM hint text, which often
 * comes back wrapped in LaTeX.
 */

// $$…$$ | \[…\] | $…$ | \(…\)  — display forms first so they win over the inline ones.
const MATH_SEGMENT =
  /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\$([^$\n]+?)\$|\\\(([\s\S]+?)\\\)/g;

// A caret exponent: `^{…}` or `^token` (letters/digits, optional leading minus).
const CARET_EXPONENT = /\^(?:\{([^}]*)\}|(-?[A-Za-z0-9]+))/g;

function KaTeXSpan({ latex, display }: { latex: string; display: boolean }) {
  const html = useMemo(
    () => katex.renderToString(latex, { throwOnError: false, displayMode: display }),
    [latex, display],
  );
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function renderProse(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let supCount = 0;
  CARET_EXPONENT.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = CARET_EXPONENT.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const exponent = match[1] ?? match[2] ?? "";
    nodes.push(<sup key={`${keyPrefix}-sup-${supCount++}`}>{exponent}</sup>);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

export function renderMathText(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let segmentCount = 0;
  MATH_SEGMENT.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MATH_SEGMENT.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(...renderProse(text.slice(lastIndex, match.index), `p${segmentCount}`));
    }
    const display = match[1] !== undefined || match[2] !== undefined;
    const latex = match[1] ?? match[2] ?? match[3] ?? match[4] ?? "";
    nodes.push(<KaTeXSpan key={`m${segmentCount}`} latex={latex} display={display} />);
    lastIndex = match.index + match[0].length;
    segmentCount++;
  }
  if (lastIndex < text.length) {
    nodes.push(...renderProse(text.slice(lastIndex), `p${segmentCount}`));
  }
  return nodes;
}

type MathTextProps = {
  children: string;
  className?: string;
};

export function MathText({ children, className }: MathTextProps) {
  const nodes = useMemo(() => renderMathText(children ?? ""), [children]);
  return <span className={className}>{nodes}</span>;
}
