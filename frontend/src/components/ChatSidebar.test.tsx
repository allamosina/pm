import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatSidebar } from "./ChatSidebar";

describe("ChatSidebar", () => {
  it("sends successful history, clears drafts and resets on remount", async () => {
    const send = vi.fn().mockResolvedValue("Done");
    const view = render(<ChatSidebar disabled={false} onSend={send} />);
    await userEvent.type(screen.getByLabelText("Message"), "Create a card");
    await userEvent.click(screen.getByText("Send message"));
    expect(send).toHaveBeenCalledWith("Create a card", []);
    expect(screen.getByLabelText("Message")).toHaveValue("");
    await userEvent.type(screen.getByLabelText("Message"), "Move it");
    await userEvent.click(screen.getByText("Send message"));
    expect(send).toHaveBeenLastCalledWith("Move it", [{ role: "user", content: "Create a card" }, { role: "assistant", content: "Done" }]);
    view.unmount();
    render(<ChatSidebar disabled={false} onSend={send} />);
    expect(screen.queryByText("Move it")).not.toBeInTheDocument();
  });

  it("keeps drafts on failure and excludes failed turns from history", async () => {
    const send = vi.fn().mockResolvedValueOnce(null).mockResolvedValueOnce("Saved");
    render(<ChatSidebar disabled={false} onSend={send} />);
    await userEvent.type(screen.getByLabelText("Message"), "Create it");
    await userEvent.click(screen.getByText("Send message"));
    expect(screen.getByLabelText("Message")).toHaveValue("Create it");
    expect(screen.queryByText("You")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Send message"));
    expect(send).toHaveBeenLastCalledWith("Create it", []);
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("prevents duplicate or blocked submissions", async () => {
    let resolve!: (value: string) => void;
    const send = vi.fn(() => new Promise<string>(r => { resolve = r; }));
    const view = render(<ChatSidebar disabled onSend={send} />);
    await userEvent.type(screen.getByLabelText("Message"), "Question");
    expect(screen.getByText("Send message")).toBeDisabled();
    view.rerender(<ChatSidebar disabled={false} onSend={send} />);
    await userEvent.click(screen.getByText("Send message"));
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
    expect(screen.getByText("Sending...")).toBeDisabled();
    await act(async () => resolve("Answer"));
    expect(send).toHaveBeenCalledOnce();
  });
});
