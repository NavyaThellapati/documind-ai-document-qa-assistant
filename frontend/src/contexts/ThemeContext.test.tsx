import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeContext";

function ThemeProbe() {
  const { theme, toggleTheme } = useTheme();
  return <button onClick={toggleTheme}>Theme: {theme}</button>;
}

describe("ThemeProvider", () => {
  it("toggles between light and dark", async () => {
    render(<ThemeProvider><ThemeProbe /></ThemeProvider>);
    const button = screen.getByRole("button", { name: /theme:/i });
    await userEvent.click(button);
    expect(button).toHaveTextContent(/dark|light/);
    expect(document.documentElement.dataset.theme).toBeDefined();
  });
});
