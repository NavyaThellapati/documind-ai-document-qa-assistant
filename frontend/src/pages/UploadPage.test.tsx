import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UploadPage } from "./UploadPage";

vi.mock("../contexts/ToastContext", () => ({
  useToast: () => ({ notify: vi.fn() }),
}));

vi.mock("../api/client", () => ({
  api: {
    uploadWithProgress: (_file: File, onProgress: (percent: number) => void) => {
      onProgress(100);
      return Promise.resolve({ message: "Document uploaded and queued for processing.", document: { status: "queued", chunk_count: 0 } });
    },
  },
}));

describe("UploadPage", () => {
  it("uploads a valid text file", async () => {
    render(<UploadPage />);
    const input = document.querySelector("input[type=file]") as HTMLInputElement;
    await userEvent.upload(input, new File(["hello"], "hello.txt", { type: "text/plain" }));
    expect(await screen.findByText(/queued for processing/i)).toBeInTheDocument();
  });
});
