import { beforeEach, describe, expect, it } from "vitest";
import {
  clearSession,
  getSession,
  getToken,
  saveSession,
} from "../auth/tokenStore";

const NOW_S = Date.now() / 1000;

describe("tokenStore", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips an unexpired session", () => {
    saveSession({ token: "tok", username: "admin", expiresAt: NOW_S + 3600 });
    expect(getSession()).toEqual({
      token: "tok",
      username: "admin",
      expiresAt: expect.any(Number),
    });
    expect(getToken()).toBe("tok");
  });

  it("treats an expired session as signed out", () => {
    // The server rejects expired tokens; keeping one would render a phantom
    // admin UI whose every admin request fails.
    saveSession({ token: "tok", username: "admin", expiresAt: NOW_S - 60 });
    expect(getSession()).toBeNull();
    expect(getToken()).toBeNull();
    // And the stale entry is gone, not resurrected next load.
    expect(localStorage.getItem("nudgemath_token")).toBeNull();
  });

  it("keeps a session without an expiry (legacy entries)", () => {
    saveSession({ token: "tok", username: "admin", expiresAt: null });
    expect(getSession()?.token).toBe("tok");
  });

  it("clearSession removes everything", () => {
    saveSession({ token: "tok", username: "admin", expiresAt: NOW_S + 3600 });
    clearSession();
    expect(getSession()).toBeNull();
  });
});
