import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthGate } from "./AuthGate";

vi.mock("./KanbanBoard", () => ({ KanbanBoard: () => <div>Private board</div> }));
afterEach(() => vi.unstubAllGlobals());
const response = (status: number) => ({ ok: status >= 200 && status < 300, status, json: async () => ({ username: "user" }) });

async function fillLogin() {
  await userEvent.type(await screen.findByLabelText("Username"), "user");
  await userEvent.type(screen.getByLabelText("Password"), "password");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("AuthGate", () => {
  it("hides the board until session validation succeeds", async () => {
    let resolve!: (value: ReturnType<typeof response>) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise(r => { resolve = r; })));
    render(<AuthGate />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking session");
    expect(screen.queryByText("Private board")).not.toBeInTheDocument();
    resolve(response(200));
    expect(await screen.findByText("Private board")).toBeInTheDocument();
  });

  it("reports invalid credentials without showing the board", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401)));
    render(<AuthGate />);
    await fillLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password");
    expect(screen.queryByText("Private board")).not.toBeInTheDocument();
  });

  it("signs in and unmounts the board on logout", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(401)).mockResolvedValueOnce(response(200)).mockResolvedValueOnce(response(204));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthGate />);
    await fillLogin();
    expect(await screen.findByText("Private board")).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][1].body).toBe(JSON.stringify({ username: "user", password: "password" }));
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText("Username")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.queryByText("Private board")).not.toBeInTheDocument();
  });

  it("offers retry when session checking is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<AuthGate />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.queryByText("Private board")).not.toBeInTheDocument();
  });

  it("does not claim logout succeeded when the server is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response(200)).mockRejectedValueOnce(new Error("offline")));
    render(<AuthGate />);
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to sign out");
    expect(screen.getByText("Private board")).toBeInTheDocument();
  });
});
