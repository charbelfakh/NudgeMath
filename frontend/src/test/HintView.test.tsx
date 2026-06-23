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
});
