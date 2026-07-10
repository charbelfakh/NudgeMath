import { MockedProvider } from "@apollo/client/testing/react";
import type { MockLink } from "@apollo/client/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { PracticeView } from "../components/PracticeView";
import {
  CurriculumDocument,
  GenerateProblemDocument,
} from "../generated/graphql";

const curriculumMock: MockLink.MockedResponse = {
  request: {
    query: CurriculumDocument,
    variables: { gradeLevel: "7" },
  },
  result: {
    data: {
      curriculum: [
        {
          __typename: "CurriculumTopicType",
          topic: "linear_equations",
          template: true,
          difficulties: ["easy", "medium", "hard"],
          description: "Solve one-variable linear equations.",
        },
        {
          __typename: "CurriculumTopicType",
          topic: "geometry",
          template: true,
          difficulties: ["easy", "medium", "hard"],
          description: "Area, perimeter, Pythagorean, angles.",
        },
        {
          __typename: "CurriculumTopicType",
          topic: "ratios",
          template: false,
          difficulties: ["easy", "medium", "hard"],
          description: "Ratio and proportion word problems.",
        },
      ],
    },
  },
};

const generateMock: MockLink.MockedResponse = {
  request: {
    query: GenerateProblemDocument,
    variables: {
      gradeLevel: "7",
      topic: null,
      difficulty: "medium",
      mode: "auto",
    },
  },
  result: {
    data: {
      generateProblem: {
        __typename: "GeneratedProblemType",
        problem: "Solve for x: 3x + 2 = 11",
        problemId: "prob-abc-123",
        gradeLevel: "7",
        topic: "linear_equations",
        difficulty: "medium",
        source: "template",
        verified: true,
        meta: {
          __typename: "HintMetaType",
          model: null,
          provider: null,
          error: null,
        },
      },
    },
  },
};

describe("PracticeView", () => {
  it("generates a problem and hides the answer in the solve flow", async () => {
    const user = userEvent.setup();

    render(
      <MockedProvider mocks={[curriculumMock, generateMock]}>
        <PracticeView />
      </MockedProvider>,
    );

    // The topic picker is populated from the grade-scoped curriculum query,
    // including the geometry topic.
    expect(
      await screen.findByRole("option", { name: /geometry \(exact\)/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate problem/i }));

    // The generated problem is shown.
    await waitFor(() =>
      expect(
        screen.getAllByText(/Solve for x: 3x \+ 2 = 11/).length,
      ).toBeGreaterThan(0),
    );

    // Practice mode hides the teacher "Correct answer" field and never renders
    // the answer text itself.
    expect(screen.queryByText(/correct answer \(teacher only/i)).toBeNull();
    expect(screen.queryByDisplayValue("x = 3")).toBeNull();
    expect(screen.queryByText("x = 3")).toBeNull();

    // The student still gets an answer box to solve.
    expect(screen.getByLabelText(/student answer/i)).toBeInTheDocument();
  });
});
