import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DocumentDetails } from "./DocumentDetails";

const completeChunk = [
  "Professional summary with complete opening text and no missing characters.",
  "",
  "- Built AI document workflows with citations",
  "- Preserved source paragraphs and bullet points",
  "- Verified document chunk rendering",
  "",
  "Detailed experience ".repeat(30).trim(),
  "Final sentence must remain visible when expanded.",
].join("\n");

vi.mock("../contexts/ToastContext", () => ({
  useToast: () => ({ notify: vi.fn() }),
}));

vi.mock("../api/client", () => ({
  api: {
    document: () => Promise.resolve({
      id: "doc-1",
      filename: "resume.txt",
      original_filename: "resume.txt",
      content_type: "text/plain",
      file_size: 4096,
      status: "ready",
      error_message: null,
      chunk_count: 1,
      page_count: 2,
      embedding_status: "ready",
      processed_at: null,
      created_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
      updated_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
      file_type: "txt",
      processing_progress: 100,
    }),
    previewDocument: () => Promise.resolve({
      document: {},
      sections: [{ page_number: 1, text: completeChunk }],
      chunks: [{ page_number: 1, chunk_number: 1, text: completeChunk }],
    }),
    reprocessBackground: vi.fn(),
    searchDocument: vi.fn(),
    downloadDocument: vi.fn(),
  },
}));

describe("DocumentDetails", () => {
  it("shows the exact full chunk text after expanding", async () => {
    render(
      <MemoryRouter initialEntries={["/documents/doc-1"]}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentDetails />} />
        </Routes>
      </MemoryRouter>,
    );

    const chunkText = await screen.findByTestId("chunk-text-1");
    expect(chunkText.textContent).not.toEqual(completeChunk);
    expect(chunkText.textContent).toMatch(/\.\.\.$/);

    await userEvent.click(screen.getByRole("button", { name: /expand/i }));

    expect(screen.getByTestId("chunk-text-1").textContent).toEqual(completeChunk);
    expect(screen.getByTestId("chunk-text-1").textContent).toContain("- Built AI document workflows with citations");
    expect(screen.getByTestId("chunk-text-1").textContent).toContain("Final sentence must remain visible when expanded.");
  });
});
