import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";

vi.mock("../api/client", () => ({
  api: {
    dashboard: () => Promise.resolve({
      total_documents: 2,
      processed_documents: 1,
      processing_documents: 1,
      failed_documents: 0,
      total_chats: 3,
      questions_asked: 7,
      storage_used_bytes: 2048,
      recent_documents: [{ id: "d1", name: "handbook.txt", status: "processed", embedding_status: "ready", created_at: new Date().toISOString() }],
      recent_conversations: [{ id: "c1", title: "Policy chat", updated_at: new Date().toISOString() }],
      ai_usage_summary: { questions_asked: 7, retrieval_top_k: 5, llm_provider: "openai" },
    }),
  },
}));

describe("Dashboard", () => {
  it("renders SaaS metrics", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(await screen.findByText("Total documents")).toBeInTheDocument();
    expect(screen.getByText("Questions asked")).toBeInTheDocument();
    expect(screen.getByText("handbook.txt")).toBeInTheDocument();
  });
});
