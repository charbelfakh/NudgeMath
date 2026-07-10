import { MockedProvider } from "@apollo/client/testing/react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import { AuthProvider } from "../auth/AuthContext";
import { saveSession } from "../auth/tokenStore";

function renderApp() {
  return render(
    <MockedProvider mocks={[]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MockedProvider>,
  );
}

describe("App tab gating", () => {
  beforeEach(() => localStorage.clear());

  it("hides the Eval tab from anonymous students", () => {
    // evaluateCase is admin-gated server-side (it fires up to two LLM calls);
    // showing the tab would just hand non-admins a permission error.
    renderApp();
    expect(screen.getByRole("button", { name: /^hint$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^practice$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^eval$/i })).toBeNull();
  });

  it("shows the Eval tab to a signed-in admin", () => {
    saveSession({
      token: "tok",
      username: "admin",
      expiresAt: Date.now() / 1000 + 3600,
    });
    renderApp();
    expect(screen.getByRole("button", { name: /^eval$/i })).toBeInTheDocument();
  });
});
