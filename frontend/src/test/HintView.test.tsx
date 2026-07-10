import { MockedProvider } from "@apollo/client/testing/react";
import type { MockLink } from "@apollo/client/testing";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { HintView } from "../components/HintView";
import {
  GenerateHintDocument,
  TranscribeProblemDocument,
} from "../generated/graphql";

const errorMock: MockLink.MockedResponse = {
  request: {
    query: GenerateHintDocument,
    variables: {
      request: {
        problem: "Solve for x: 2x - 5 = 9",
        studentAnswer: "x = 2",
        correctAnswer: null,
        problemId: null,
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
        problemId: null,
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
        problemId: null,
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

// FileReader in jsdom encodes the File bytes as a data URL; base64("img") === "aW1n".
const transcribeMock: MockLink.MockedResponse = {
  request: {
    query: TranscribeProblemDocument,
    variables: { image: "data:image/png;base64,aW1n" },
  },
  result: {
    data: {
      transcribeProblem: {
        __typename: "TranscriptionType",
        problem: "What is 7 x 8?",
        studentAnswer: "54",
        meta: {
          __typename: "HintMetaType",
          model: "llama3.2-vision",
          provider: "ollama",
          latencyMs: 120,
          error: null,
        },
      },
    },
  },
};

// Same transcription payload, keyed to a webp data URL (base64("img") === "aW1n").
const webpDropMock: MockLink.MockedResponse = {
  request: {
    query: TranscribeProblemDocument,
    variables: { image: "data:image/webp;base64,aW1n" },
  },
  result: transcribeMock.result,
};

describe("HintView", () => {
  it("fills the problem and answer from an uploaded image", async () => {
    const user = userEvent.setup();

    render(
      <MockedProvider mocks={[transcribeMock]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["img"], "problem.png", { type: "image/png" });
    await user.upload(
      screen.getByLabelText(/upload a photo or screenshot of a problem/i),
      file,
    );

    // Transcribed text lands in the editable problem + answer fields.
    await waitFor(() =>
      expect(screen.getByDisplayValue("What is 7 x 8?")).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("54")).toBeInTheDocument();
  });

  it("accepts gif and webp in the file picker", () => {
    render(
      <MockedProvider mocks={[]}>
        <HintView />
      </MockedProvider>,
    );
    const accept =
      screen
        .getByLabelText(/upload a photo or screenshot of a problem/i)
        .getAttribute("accept") ?? "";
    expect(accept).toContain("image/gif");
    expect(accept).toContain("image/webp");
  });

  it("transcribes a webp image dropped onto the drop zone", async () => {
    render(
      <MockedProvider mocks={[webpDropMock]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["img"], "problem.webp", { type: "image/webp" });
    fireEvent.drop(screen.getByTestId("image-dropzone"), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() =>
      expect(screen.getByDisplayValue("What is 7 x 8?")).toBeInTheDocument(),
    );
  });

  it("rejects a non-image drop with a clear error", async () => {
    render(
      <MockedProvider mocks={[]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.drop(screen.getByTestId("image-dropzone"), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        /unsupported file type/i,
      ),
    );
    // A rejected file must not leave a preview behind.
    expect(screen.queryByAltText(/uploaded problem image/i)).toBeNull();
  });

  it("shows the uploaded image and can remove it", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[transcribeMock]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["img"], "problem.png", { type: "image/png" });
    await user.upload(
      screen.getByLabelText(/upload a photo or screenshot of a problem/i),
      file,
    );

    const preview = await screen.findByAltText(/uploaded problem image/i);
    expect(preview).toHaveAttribute("src", "data:image/png;base64,aW1n");

    await user.click(screen.getByRole("button", { name: /remove image/i }));
    expect(screen.queryByAltText(/uploaded problem image/i)).toBeNull();
  });

  it("rejects an oversized image before uploading it", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["img"], "huge.png", { type: "image/png" });
    // Fake the size rather than allocating megabytes in jsdom.
    Object.defineProperty(file, "size", { value: 7 * 1024 * 1024 });

    await user.upload(
      screen.getByLabelText(/upload a photo or screenshot of a problem/i),
      file,
    );

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/too large/i),
    );
    // Never read, never previewed, never sent — the mock link would throw on a call.
    expect(screen.queryByAltText(/uploaded problem image/i)).toBeNull();
  });

  it("shows the dropped image in the preview", async () => {
    render(
      <MockedProvider mocks={[webpDropMock]}>
        <HintView />
      </MockedProvider>,
    );

    const file = new File(["img"], "problem.webp", { type: "image/webp" });
    fireEvent.drop(screen.getByTestId("image-dropzone"), {
      dataTransfer: { files: [file] },
    });

    const preview = await screen.findByAltText(/uploaded problem image/i);
    expect(preview).toHaveAttribute("src", "data:image/webp;base64,aW1n");
  });

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
