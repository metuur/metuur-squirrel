import { describe, it, expect, vi, afterEach } from "vitest";
import { api, ApiError } from "./client";

// Story in-app-vault-onboarding 4.1 — client methods for the onboarding wizard.
// Covers R-2.1 (obsidianStatus) and R-3.3 (setVaultConfig + error mapping).

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as Response);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api.obsidianStatus", () => {
  it("GETs /api/env/obsidian and returns the typed shape", async () => {
    const f = mockFetch(200, { installed: true, path: "/Applications/Obsidian.app" });
    vi.stubGlobal("fetch", f);
    const res = await api.obsidianStatus();
    expect(res).toEqual({ installed: true, path: "/Applications/Obsidian.app" });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:3939/api/env/obsidian");
    expect(init?.method ?? "GET").toBe("GET");
  });
});

describe("api.setVaultConfig", () => {
  it("POSTs /api/config/vault with the body", async () => {
    const f = mockFetch(200, { name: "personal", path: "/Users/x/v", default: true });
    vi.stubGlobal("fetch", f);
    const res = await api.setVaultConfig({ path: "~/v", create: true });
    expect(res).toEqual({ name: "personal", path: "/Users/x/v", default: true });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://127.0.0.1:3939/api/config/vault");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ path: "~/v", create: true });
  });

  it("maps a 400 error body to ApiError with the server message", async () => {
    vi.stubGlobal("fetch", mockFetch(400, { error: "Vault path must be inside your home directory." }));
    await expect(api.setVaultConfig({ path: "/tmp/x" })).rejects.toMatchObject({
      status: 400,
      message: "Vault path must be inside your home directory.",
    });
    await expect(api.setVaultConfig({ path: "/tmp/x" })).rejects.toBeInstanceOf(ApiError);
  });
});
