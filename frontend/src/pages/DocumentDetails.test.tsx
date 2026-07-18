import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentDetails } from "./DocumentDetails";

const apiMocks = vi.hoisted(() => ({
  documentInsight: vi.fn(),
  explainDocument: vi.fn(),
  ask: vi.fn(),
}));

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
    documentInsight: apiMocks.documentInsight.mockImplementation((_id: string, summaryLength = "standard") => Promise.resolve({
      id: "insight-1",
      document_id: "doc-1",
      summary_length: summaryLength,
      document_type: "resume",
      status: "ready",
      overview: "Resume covering AI document workflow experience.",
      summary: "The resume summarizes AI document workflow experience, backend skills, and project work without reproducing the source text.",
      key_points: ["Built AI document workflows with citations"],
      main_sections: [
        { title: "Professional Summary", description: "Introduces the candidate's AI document workflow background." },
        { title: "Experience", description: "Highlights relevant implementation work." },
        { title: "Projects", description: "Covers document Q&A projects." },
      ],
      key_entities: [{ name: "Python", type: "technology" }, { name: "FastAPI", type: "technology" }],
      suggested_questions: ["What backend technologies does this candidate use?"],
      sources: [{ page_number: 1, chunk_number: 1, excerpt: "Professional summary" }],
      notice: "Basic summary generated without an LLM.",
      llm_configured: false,
      created_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
      updated_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
    })),
    explainDocument: apiMocks.explainDocument.mockImplementation((_id: string, summaryLength = "standard") => Promise.resolve({
      id: "insight-1",
      document_id: "doc-1",
      summary_length: summaryLength,
      document_type: "resume",
      status: "ready",
      overview: "Resume covering regenerated AI document workflow experience.",
      summary: "A regenerated summary describes backend skills and project work concisely.",
      key_points: ["Regenerated summary stays concise"],
      main_sections: [{ title: "Projects", description: "Covers document Q&A projects." }],
      key_entities: [{ name: "Python", type: "technology" }],
      suggested_questions: ["What backend technologies does this candidate use?"],
      sources: [{ page_number: 1, chunk_number: 1, excerpt: "Professional summary" }],
      notice: "Basic summary generated without an LLM.",
      llm_configured: false,
      created_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
      updated_at: new Date("2026-01-01T00:00:00.000Z").toISOString(),
    })),
    ask: apiMocks.ask,
    reprocessBackground: vi.fn(),
    searchDocument: vi.fn(),
    downloadDocument: vi.fn(),
  },
}));

describe("DocumentDetails", () => {
  beforeEach(() => {
    apiMocks.documentInsight.mockClear();
    apiMocks.explainDocument.mockClear();
    apiMocks.ask.mockClear();
  });

  it("shows the exact full chunk text after expanding", async () => {
    render(
      <MemoryRouter initialEntries={["/documents/doc-1"]}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentDetails />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Resume covering AI document workflow experience.")).toBeInTheDocument();
    expect(screen.getByText("resume")).toBeInTheDocument();
    expect(screen.getByText("Python · technology")).toBeInTheDocument();
    expect(screen.queryByText("Chunk viewer")).not.toBeInTheDocument();
    expect(screen.queryByText("Final sentence must remain visible when expanded.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /chunks/i }));

    const chunkText = await screen.findByTestId("chunk-text-1");
    expect(chunkText.textContent).not.toEqual(completeChunk);
    expect(chunkText.textContent).toMatch(/\.\.\.$/);

    await userEvent.click(screen.getByRole("button", { name: /expand full chunk/i }));

    expect(screen.getByTestId("chunk-text-1").textContent).toEqual(completeChunk);
    expect(screen.getByTestId("chunk-text-1").textContent).toContain("- Built AI document workflows with citations");
    expect(screen.getByTestId("chunk-text-1").textContent).toContain("Final sentence must remain visible when expanded.");
  });

  it("changes summary length, regenerates, and populates Ask AI from suggested questions", async () => {
    render(
      <MemoryRouter initialEntries={["/documents/doc-1"]}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentDetails />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Resume covering AI document workflow experience.")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/summary length/i), "detailed");
    expect(await screen.findByText("detailed")).toBeInTheDocument();
    expect(apiMocks.documentInsight).toHaveBeenLastCalledWith("doc-1", "detailed");

    await userEvent.click(screen.getByRole("button", { name: /regenerate summary/i }));
    expect(await screen.findByText("Resume covering regenerated AI document workflow experience.")).toBeInTheDocument();
    expect(apiMocks.explainDocument).toHaveBeenCalledWith("doc-1", "detailed");

    await userEvent.click(screen.getByRole("button", { name: /what backend technologies/i }));
    expect(screen.getByRole("tab", { name: /ask ai/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText(/ask a question about this document/i)).toHaveValue("What backend technologies does this candidate use?");
  });
});
