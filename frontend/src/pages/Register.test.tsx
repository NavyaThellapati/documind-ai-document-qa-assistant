import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Register } from "./Register";

const register = vi.fn();

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ register }),
}));

describe("Register", () => {
  it("submits a new account", async () => {
    render(<MemoryRouter><Register /></MemoryRouter>);
    await userEvent.type(screen.getByLabelText(/name/i), "New User");
    await userEvent.type(screen.getByLabelText(/email/i), "new@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "Strongpass123");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(register).toHaveBeenCalledWith("new@example.com", "Strongpass123", "New User");
  });
});
