import { MockedProvider } from "@apollo/client/testing/react";
import type { MockLink } from "@apollo/client/testing";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PracticeView } from "../components/PracticeView";
import { AdminLogin } from "../components/AdminLogin";
import { AdminPanel } from "../components/AdminPanel";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import {
  AdminModelsDocument,
  ClaudeSubscriptionDocument,
  CurriculumDocument,
  FinishClaudeLoginDocument,
  GenerateProblemDocument,
  LoginDocument,
  RevealAnswerDocument,
  SetClaudeEffortDocument,
  SolveProblemDocument,
  StartClaudeLoginDocument,
} from "../generated/graphql";

const curriculumMock: MockLink.MockedResponse = {
  request: { query: CurriculumDocument, variables: { gradeLevel: "7" } },
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
      ],
    },
  },
};

const generateMock: MockLink.MockedResponse = {
  request: {
    query: GenerateProblemDocument,
    variables: { gradeLevel: "7", topic: null, difficulty: "medium", mode: "auto" },
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

const revealMock: MockLink.MockedResponse = {
  request: { query: RevealAnswerDocument, variables: { problemId: "prob-abc-123" } },
  result: {
    data: {
      revealAnswer: {
        __typename: "RevealedAnswerType",
        problemId: "prob-abc-123",
        correctAnswer: "x = 3",
        found: true,
      },
    },
  },
};

function LoginHarness() {
  const { isAdmin, session } = useAuth();
  return isAdmin ? <p>signed in as {session?.username}</p> : <AdminLogin />;
}

describe("admin", () => {
  beforeEach(() => localStorage.clear());

  it("does not show the reveal control to non-admins", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[curriculumMock, generateMock]}>
        <PracticeView />
      </MockedProvider>,
    );
    await user.click(screen.getByRole("button", { name: /generate problem/i }));
    await waitFor(() =>
      expect(screen.getAllByText(/Solve for x: 3x \+ 2 = 11/).length).toBeGreaterThan(0),
    );
    expect(screen.queryByRole("button", { name: /reveal answer/i })).toBeNull();
  });

  it("reveals the stored answer for an admin on demand", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[curriculumMock, generateMock, revealMock]}>
        <PracticeView isAdmin />
      </MockedProvider>,
    );
    await user.click(screen.getByRole("button", { name: /generate problem/i }));

    const revealBtn = await screen.findByRole("button", { name: /reveal answer/i });
    // The answer value is not on screen until the admin explicitly asks.
    expect(screen.queryByText(/x = 3/)).toBeNull();

    await user.click(revealBtn);
    await waitFor(() => expect(screen.getByText(/x = 3/)).toBeInTheDocument());
  });

  it("does not show the solve control to non-admins", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[curriculumMock, generateMock]}>
        <PracticeView />
      </MockedProvider>,
    );
    await user.click(screen.getByRole("button", { name: /generate problem/i }));
    await waitFor(() =>
      expect(screen.getAllByText(/Solve for x: 3x \+ 2 = 11/).length).toBeGreaterThan(0),
    );
    expect(screen.queryByRole("button", { name: /generate solution/i })).toBeNull();
  });

  it("generates a worked solution for an admin on demand", async () => {
    const solveMock: MockLink.MockedResponse = {
      request: {
        query: SolveProblemDocument,
        variables: { problem: "Solve for x: 3x + 2 = 11", gradeLevel: "7" },
      },
      result: {
        data: {
          solveProblem: {
            __typename: "SolutionType",
            solutionText: "1. Subtract 2: 3x = 9\n2. Divide by 3: x = 3",
            finalAnswer: "x = 3",
            meta: {
              __typename: "HintMetaType",
              model: "test-solver",
              provider: "mock",
              latencyMs: 12,
              error: null,
            },
          },
        },
      },
    };
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[curriculumMock, generateMock, solveMock]}>
        <PracticeView isAdmin />
      </MockedProvider>,
    );
    await user.click(screen.getByRole("button", { name: /generate problem/i }));

    const solveBtn = await screen.findByRole("button", {
      name: /generate solution/i,
    });
    await user.click(solveBtn);

    await waitFor(() =>
      expect(screen.getByText(/Divide by 3/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/final answer/i)).toBeInTheDocument();
    // The separate solver model is visible so the admin can verify what solved it.
    expect(screen.getByText(/test-solver/)).toBeInTheDocument();
  });

  it("establishes a session on successful login", async () => {
    const loginMock: MockLink.MockedResponse = {
      request: {
        query: LoginDocument,
        variables: { username: "admin", password: "secret" },
      },
      result: {
        data: {
          login: {
            __typename: "AuthPayloadType",
            token: "tok-123",
            username: "admin",
            expiresAt: 9999999999,
            error: null,
          },
        },
      },
    };
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[loginMock]}>
        <AuthProvider>
          <LoginHarness />
        </AuthProvider>
      </MockedProvider>,
    );

    await user.type(screen.getByLabelText(/username/i), "admin");
    await user.type(screen.getByLabelText(/^password$/i), "secret");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(screen.getByText(/signed in as admin/i)).toBeInTheDocument(),
    );
    expect(localStorage.getItem("nudgemath_token")).toBe("tok-123");
  });

  it("toggles password visibility", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[]}>
        <AuthProvider>
          <LoginHarness />
        </AuthProvider>
      </MockedProvider>,
    );
    const pw = screen.getByLabelText(/^password$/i);
    expect(pw).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: /show password/i }));
    expect(pw).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: /hide password/i }));
    expect(pw).toHaveAttribute("type", "password");
  });

  it("shows an error on failed login", async () => {
    const loginMock: MockLink.MockedResponse = {
      request: {
        query: LoginDocument,
        variables: { username: "admin", password: "nope" },
      },
      result: {
        data: {
          login: {
            __typename: "AuthPayloadType",
            token: null,
            username: null,
            expiresAt: null,
            error: "Invalid username or password.",
          },
        },
      },
    };
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[loginMock]}>
        <AuthProvider>
          <LoginHarness />
        </AuthProvider>
      </MockedProvider>,
    );

    await user.type(screen.getByLabelText(/username/i), "admin");
    await user.type(screen.getByLabelText(/^password$/i), "nope");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid username or password/i),
    );
    expect(screen.queryByText(/signed in/i)).toBeNull();
  });
});

const adminModelsMock: MockLink.MockedResponse = {
  request: { query: AdminModelsDocument },
  result: {
    data: {
      adminModels: {
        __typename: "AdminModelsType",
        visionModel: "llama3.2-vision",
        generationModel: "llama3.2",
        solverModel: "llama3.2",
        visionPresets: [
          {
            __typename: "ModelPresetType",
            name: "llama3.2-vision",
            provider: "ollama",
            model: "llama3.2-vision",
          },
        ],
        generationPresets: [
          {
            __typename: "ModelPresetType",
            name: "llama3.2",
            provider: "ollama",
            model: "llama3.2",
          },
        ],
        solverPresets: [
          {
            __typename: "ModelPresetType",
            name: "llama3.2",
            provider: "ollama",
            model: "llama3.2",
          },
        ],
      },
    },
  },
};

function claudeStatusMock(signedIn: boolean): MockLink.MockedResponse {
  return {
    request: { query: ClaudeSubscriptionDocument },
    result: {
      data: {
        claudeSubscription: {
          __typename: "ClaudeSubscriptionStatusType",
          signedIn,
          detail: signedIn
            ? "Signed in — pick a Claude model (Sonnet/Opus/Haiku) in the dropdowns above."
            : "Not signed in — click Connect to sign in with your Claude subscription.",
          model: "claude-sonnet-5",
          effort: null,
        },
      },
    },
  };
}

const startLoginMock: MockLink.MockedResponse = {
  request: { query: StartClaudeLoginDocument },
  result: {
    data: {
      startClaudeLogin: {
        __typename: "ClaudeLoginStartType",
        signedIn: false,
        url: "https://claude.ai/oauth/authorize?code=true",
      },
    },
  },
};

describe("admin panel · claude subscription", () => {
  beforeEach(() => {
    // jsdom does not implement window.open; stub it so Connect does not warn.
    vi.stubGlobal("open", vi.fn());
  });

  it("shows a not-connected state and hides unavailable models", async () => {
    render(
      <MockedProvider mocks={[adminModelsMock, claudeStatusMock(false)]}>
        <AdminPanel />
      </MockedProvider>,
    );
    expect(await screen.findByText(/not connected/i)).toBeInTheDocument();
    // Only the available (ollama) generation preset is offered by the resolver.
    const generation = await screen.findByRole("combobox", { name: /generation/i });
    expect(generation).toHaveTextContent("llama3.2");
    expect(generation).not.toHaveTextContent("claude-sonnet-5");
    expect(generation).not.toHaveTextContent("claude-opus-4-8");
  });

  it("shows the effort selector when connected and sets the level", async () => {
    const setEffortMock: MockLink.MockedResponse = {
      request: {
        query: SetClaudeEffortDocument,
        variables: { effort: "xhigh" },
      },
      result: {
        data: {
          setClaudeEffort: {
            __typename: "ClaudeSubscriptionStatusType",
            signedIn: true,
            effort: "xhigh",
          },
        },
      },
    };
    const user = userEvent.setup();
    render(
      <MockedProvider
        mocks={[
          adminModelsMock,
          claudeStatusMock(true),
          setEffortMock,
          claudeStatusMock(true), // refetch after the mutation
        ]}
      >
        <AdminPanel />
      </MockedProvider>,
    );

    const effort = await screen.findByRole("combobox", { name: /effort/i });
    expect(effort).toHaveValue(""); // API default
    await user.selectOptions(effort, "xhigh");
    // The mutation fired with the chosen level (mock would error otherwise).
    await waitFor(() => expect(effort).toBeEnabled());
  });

  it("reveals the paste-code box after clicking Connect", async () => {
    const user = userEvent.setup();
    render(
      <MockedProvider mocks={[adminModelsMock, claudeStatusMock(false), startLoginMock]}>
        <AdminPanel />
      </MockedProvider>,
    );
    await user.click(await screen.findByRole("button", { name: /^connect$/i }));
    expect(
      await screen.findByLabelText(/authorization code/i),
    ).toBeInTheDocument();
  });

  it("surfaces an error when the pasted code is rejected", async () => {
    const finishErrMock: MockLink.MockedResponse = {
      request: { query: FinishClaudeLoginDocument, variables: { code: "bad" } },
      result: {
        data: {
          finishClaudeLogin: {
            __typename: "ClaudeLoginResultType",
            signedIn: false,
            detail: "",
            error: "State mismatch — restart the sign-in and try again.",
          },
        },
      },
    };
    const user = userEvent.setup();
    render(
      <MockedProvider
        mocks={[adminModelsMock, claudeStatusMock(false), startLoginMock, finishErrMock]}
      >
        <AdminPanel />
      </MockedProvider>,
    );
    await user.click(await screen.findByRole("button", { name: /^connect$/i }));
    await user.type(await screen.findByLabelText(/authorization code/i), "bad");
    await user.click(screen.getByRole("button", { name: /finish/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/state mismatch/i),
    );
  });
});
