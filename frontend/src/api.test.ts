import { api, ApiError, tokenStore } from "./api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  tokenStore.clear();
});

describe("api client", () => {
  it("sends the bearer token and hits the real backend route", async () => {
    tokenStore.set("tok");
    const fn = mockFetch(200, []);
    await api.projects();
    const [url, init] = fn.mock.calls[0];
    expect(url).toMatch(/\/api\/projects$/);
    expect(init.headers.Authorization).toBe("Bearer tok");
  });
  it("maps backend error envelopes to ApiError", async () => {
    mockFetch(409, { error: { code: "llm_not_configured", message: "GROQ_API_KEY is not set" } });
    await expect(api.startRun(1)).rejects.toMatchObject({
      status: 409,
      code: "llm_not_configured",
      message: "GROQ_API_KEY is not set",
    });
  });
  it("maps FastAPI validation errors", async () => {
    mockFetch(422, { detail: [{ msg: "String should have at least 8 characters" }] });
    await expect(api.register("a@b.co", "x")).rejects.toBeInstanceOf(ApiError);
  });
  it("reports network failure clearly", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fail")));
    await expect(api.status()).rejects.toMatchObject({ code: "network" });
  });
  it("uses the documented routes for approvals", async () => {
    const fn = mockFetch(200, {});
    await api.approvePlan(7, true);
    await api.approveChange(3);
    await api.applyChanges(7);
    expect(fn.mock.calls.map((c) => c[0].replace(/^.*\/api/, ""))).toEqual([
      "/runs/7/approve-plan",
      "/changes/3/approve",
      "/runs/7/apply-changes",
    ]);
    expect(JSON.parse(fn.mock.calls[0][1].body)).toEqual({ confirm_dependencies: true });
  });
});
