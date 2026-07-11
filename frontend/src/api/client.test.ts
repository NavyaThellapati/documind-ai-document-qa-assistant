import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

describe("api client", () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sends bearer token for document downloads", async () => {
    localStorage.setItem("documind_token", "test-token");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(["document"])),
    });
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:documind");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    await api.downloadDocument("doc-1", "document.txt");

    expect(fetchMock).toHaveBeenCalledWith("/api/documents/doc-1/download", {
      headers: { Authorization: "Bearer test-token" },
    });
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:documind");
  });
});
