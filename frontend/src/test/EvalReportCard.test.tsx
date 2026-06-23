import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvalReportCard, type EvalReportData } from "../components/EvalReportCard";

const cannedReport: EvalReportData = {
  passed: false,
  caseId: "algebra_sign_error",
  problem: "Solve for x: 2x - 5 = 9",
  hintText: "Check the sign when moving terms.",
  revealsAnswer: false,
  summary: "FAIL — does_not_reveal_answer: leaked",
  meta: { model: "claude-sonnet-4-6", latencyMs: 120, error: null },
  flagDisagreement: true,
  modelAnswerDisagreement: null,
  deterministic: {
    passed: false,
    checks: [
      {
        name: "does_not_reveal_answer",
        passed: false,
        detail: "Hint text contains the correct answer value '7'.",
      },
      {
        name: "non_empty",
        passed: true,
        detail: "Hint text is non-empty.",
      },
    ],
  },
  judge: {
    passed: true,
    score: 0.75,
    checks: [
      {
        name: "addresses_specific_error",
        passed: true,
        detail: "Targets sign error.",
      },
    ],
    meta: { model: "claude-sonnet-4-6", latencyMs: 90, error: null },
  },
};

describe("EvalReportCard", () => {
  it("renders overall verdict and deterministic checks", () => {
    render(<EvalReportCard report={cannedReport} />);

    expect(screen.getByText("Overall")).toBeInTheDocument();
    expect(screen.getAllByText("FAIL").length).toBeGreaterThan(0);
    expect(screen.getByText("does_not_reveal_answer")).toBeInTheDocument();
    expect(
      screen.getByText("Hint text contains the correct answer value '7'."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Flag disagreement:/)).toBeInTheDocument();
    expect(screen.getByText(/yes/)).toBeInTheDocument();
  });
});
