import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPage } from "./ChatPage";

vi.mock("../contexts/ToastContext", () => ({
  useToast: () => ({ notify: vi.fn() }),
}));

vi.mock("../api/client", () => ({
  api: {
    documents: () => Promise.resolve({ documents: [{ id: "d1", original_filename: "guide.txt", status: "processed" }] }),
    conversations: () => Promise.resolve([]),
    streamAsk: async (_payload: unknown, onToken: (token: string) => void) => {
      onToken("Grounded ");
      onToken("answer");
      return { conversation_id: "c1", message_id: "m1", answer: "Grounded answer", sources: [] };
    },
    feedback: () => Promise.resolve({}),
  },
}));

describe("ChatPage", () => {
  it("streams an answer into the chat", async () => {
    render(<ChatPage />);
    await userEvent.type(screen.getByPlaceholderText(/ask a question/i), "What is in the guide?");
    await userEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(await screen.findByText("Grounded answer")).toBeInTheDocument();
  });
});
