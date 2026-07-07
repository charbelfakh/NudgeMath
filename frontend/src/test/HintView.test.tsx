import { MockedProvider } from "@apollo/client/testing/react";
import type { MockLink } from "@apollo/client/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { HintView } from "../components/HintView";
import { GenerateHintDocument } from "../generated/graphql";

const errorMock: MockLink.MockedResponse = {
  request: {
    query: GenerateHintDocument,
    variables: {
      request: {
        problem: "Solve for x: 2x - 5 = 9",
        studentAnswer: "x = 2",
        correctAnswer: null,
        gradeLevel: null,
        subject: null,
        history: null,
      },
    },
  },
  result: {
    data: {
      generateHint: {
        __typename: "HintType",
        hintText: "Unable to parse model response.",
        revealsAnswer: false,
        answerCorrect: false,
        meta: {
          __typename: "HintMetaType",
          model: "claude-sonnet-4-6",
          latencyMs: 50,
          error: "JSON parse error: Expecting value",
        },
      },
    },
  },
};

const FIRST_HINT = "Check the sign when you move -5 across.";
const SECOND_HINT = "Good — now subtract correctly on both sides.";

const firstTurnMock: MockLink.MockedResponse = {
  request: {
    query: GenerateHintDocument,
    variables: {
      request: {
        problem: "Solve for x: 2x - 5 = 9",
        studentAnswer: "x = 2",
        correctAnswer: null,
        gradeLevel: null,
        subject: null,
        history: null,
      },
    },
  },
  result: {
    data: {
      generateHint: {
        __typename: "HintType",
        hintText: FIRST_HINT,
        revealsAnswer: false,
        answerCorrect: false,
        meta: {
          __typename: "HintMetaType",
          model: "llama3.2",
          latencyMs: 40,
          error: null,
        },
      },
    },
  },
};

const followUpMock: MockLink.MockedResponse = {
  request: {
    query: GenerateHintDocument,
    variables: {
      request: {
        problem: "Solve for x: 2x - 5 = 9",
        studentAnswer: "x = 4",
        correctAnswer: null,
        gradeLevel: null,
        subject: null,
        history: [
          { role: "student", text: "x = 2" },
          { role: "tutor", text: FIRST_HINT },
        ],
      },
    },
  },
  result: {
    data: {
      generateHint: {
        __typename: "HintType",
        hintText: SECOND_HINT,
        revealsAnswer: false,
        answerCorrect: false,
        meta: {
          __typename: "HintMetaType",
          model: "llama3.2",
          latencyMs: 42,
          error: null,
        },
      },
    },
  },
};

describe("HintView", () => {
  it("shows meta.error partial-success state", async () => {
    const user = userEvent.setup();

    render(
      <MockedProvider mocks={[errorMock]}>
        <HintView />
      </MockedProvider>,
    );

    await user.click(screen.getByRole("button", { name: /generate hint/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /Generation error: JSON parse error/,
      );
    });
  });

  it("sends prior turns as history on a follow-up attempt", async () => {
    const user = userEvent.setup();

    render(
      <MockedProvider mocks={[firstTurnMock, followUpMock]}>
        <HintView />
      </MockedProvider>,
    );

    // First attempt (default student answer "x = 2") → first hint enters the thread.
    await user.click(screen.getByRole("button", { name: /generate hint/i }));
    await waitFor(() => expect(screen.getByText(FIRST_HINT)).toBeInTheDocument());

    // Second attempt: the answer field is cleared, type a new attempt and resubmit.
    // followUpMock only matches if the accumulated history is sent, so a passing
    // assertion proves the multi-turn wiring end to end.
    await user.type(screen.getByLabelText(/your next attempt/i), "x = 4");
    await user.click(screen.getByRole("button", { name: /send next attempt/i }));

    await waitFor(() => expect(screen.getByText(SECOND_HINT)).toBeInTheDocument());
    // The first hint is still visible in the conversation thread.
    expect(screen.getByText(FIRST_HINT)).toBeInTheDocument();
  });
});
