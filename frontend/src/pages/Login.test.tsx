import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Login } from "./Login";

const login = vi.fn();

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ login }),
}));

describe("Login", () => {
  it("submits credentials", async () => {
    render(<MemoryRouter><Login /></MemoryRouter>);
    await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "Strongpass123");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(login).toHaveBeenCalledWith("user@example.com", "Strongpass123");
  });
});
