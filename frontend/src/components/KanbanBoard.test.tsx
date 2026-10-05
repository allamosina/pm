import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/test/board-fixture";

const response = (data = initialData, status = 200) => ({ ok: status === 200, status, json: async () => structuredClone(data) });
afterEach(() => vi.unstubAllGlobals());
async function setup() {
  const fetchMock = vi.fn().mockResolvedValue(response());
  vi.stubGlobal("fetch", fetchMock);
  const expired = vi.fn();
  render(<KanbanBoard onSessionExpired={expired} />);
  const column = await screen.findByTestId("column-col-backlog");
  return { fetchMock, expired, column };
}

describe("persistent KanbanBoard", () => {
  it("loads five columns and commits renames only on save", async () => {
    const { fetchMock, column } = await setup();
    expect(screen.getAllByTestId(/column-/)).toHaveLength(5);
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Ideas");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const next = structuredClone(initialData);
    next.columns[0].title = "Ideas"; next.revision = 1;
    fetchMock.mockResolvedValueOnce(response(next));
    await userEvent.click(within(column).getByText("Save column"));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/board/columns/col-backlog");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ title: "Ideas", expected_revision: 0 });
    expect(screen.getByText("Ideas")).toBeInTheDocument();
  });

  it("adds and deletes using server IDs and the latest revision", async () => {
    const { fetchMock, column } = await setup();
    await userEvent.click(within(column).getByText("Add a card"));
    await userEvent.type(within(column).getByLabelText("Card title"), "New card");
    const next = structuredClone(initialData);
    next.cards.server = { id: "server", title: "New card", details: "" };
    next.columns[0].cardIds.push("server"); next.revision = 1;
    fetchMock.mockResolvedValueOnce(response(next));
    await userEvent.click(within(column).getByText("Add card"));
    expect(await screen.findByTestId("card-server")).toBeInTheDocument();
    fetchMock.mockResolvedValueOnce(response({ ...initialData, revision: 2 }));
    await userEvent.click(screen.getByLabelText("Delete New card"));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/board/cards/server?expected_revision=1");
    expect(screen.queryByTestId("card-server")).not.toBeInTheDocument();
  });

  it("cancels editing and preserves drafts when a save fails", async () => {
    const { fetchMock } = await setup();
    await userEvent.click(screen.getByLabelText("Edit Align roadmap themes"));
    await userEvent.clear(screen.getByLabelText("Card title"));
    await userEvent.type(screen.getByLabelText("Card title"), "Draft title");
    await userEvent.click(screen.getByText("Cancel"));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByLabelText("Edit Align roadmap themes"));
    expect(screen.getByLabelText("Card title")).toHaveValue("Align roadmap themes");
    await userEvent.clear(screen.getByLabelText("Card title"));
    await userEvent.type(screen.getByLabelText("Card title"), "Saved title");
    fetchMock.mockResolvedValueOnce(response(initialData, 503));
    await userEvent.click(screen.getByText("Save card"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to save");
    expect(screen.getByLabelText("Card title")).toHaveValue("Saved title");
    const next = structuredClone(initialData); next.cards["card-1"].title = "Saved title";
    fetchMock.mockResolvedValueOnce(response(next));
    await userEvent.click(screen.getByText("Save card"));
    expect(await screen.findByRole("heading", { name: "Saved title" })).toBeInTheDocument();
  });

  it("reloads authoritative state after a conflict", async () => {
    const { fetchMock } = await setup();
    const next = structuredClone(initialData); next.revision = 7; next.cards["card-1"].title = "Changed elsewhere";
    fetchMock.mockResolvedValueOnce(response(initialData, 409)).mockResolvedValueOnce(response(next));
    await userEvent.click(screen.getByLabelText("Delete Align roadmap themes"));
    expect(await screen.findByText("Changed elsewhere")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("changed elsewhere");
  });

  it("locks mutations until reload succeeds after an uncertain save", async () => {
    const { fetchMock } = await setup();
    fetchMock.mockRejectedValueOnce(new Error("offline")).mockRejectedValueOnce(new Error("offline"));
    await userEvent.click(screen.getByLabelText("Delete Align roadmap themes"));
    expect(await screen.findByText("Reload board")).toBeInTheDocument();
    expect(screen.getByLabelText("Delete Align roadmap themes")).toBeDisabled();
    await userEvent.click(screen.getByText("Reload board"));
    expect(screen.getByLabelText("Delete Align roadmap themes")).toBeEnabled();
  });

  it("prevents overlapping saves", async () => {
    const { fetchMock } = await setup();
    let resolve!: (value: ReturnType<typeof response>) => void;
    fetchMock.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    await userEvent.click(screen.getByLabelText("Delete Align roadmap themes"));
    expect(screen.getByText("Saving...")).toBeInTheDocument();
    expect(screen.getByLabelText("Delete Gather customer signals")).toBeDisabled();
    await act(async () => resolve(response()));
  });

  it("expires the session on a mutation 401", async () => {
    const { fetchMock, expired } = await setup();
    fetchMock.mockResolvedValueOnce(response(initialData, 401));
    await userEvent.click(screen.getByLabelText("Delete Align roadmap themes"));
    expect(expired).toHaveBeenCalledOnce();
  });

  it("shows loading, load failure, and retry", async () => {
    const mock = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue(response());
    vi.stubGlobal("fetch", mock);
    render(<KanbanBoard onSessionExpired={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    await userEvent.click(await screen.findByText("Try again"));
    expect(await screen.findByTestId("column-col-backlog")).toBeInTheDocument();
  });
});

it("adopts AI board responses and locks manual saves during chat", async () => {
  const { fetchMock } = await setup();
  let resolve!: (value: unknown) => void;
  fetchMock.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
  await userEvent.type(screen.getByLabelText("Message"), "Edit the first card");
  await userEvent.click(screen.getByText("Send message"));
  expect(screen.getByLabelText("Delete Align roadmap themes")).toBeDisabled();
  const next = structuredClone(initialData);
  next.cards["card-1"].title = "AI edited title";
  await act(async () => resolve({ ok: true, json: async () => ({ reply: "Edited.", board: next }) }));
  expect(await screen.findByText("AI edited title")).toBeInTheDocument();
  expect(screen.getByText("Edited.")).toBeInTheDocument();
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ question: "Edit the first card", history: [] });
});

it("keeps the chat draft and reloads state on a failed AI call", async () => {
  const { fetchMock } = await setup();
  fetchMock.mockResolvedValueOnce(response(initialData, 502));
  await userEvent.type(screen.getByLabelText("Message"), "Create a card");
  await userEvent.click(screen.getByText("Send message"));
  expect(screen.getByLabelText("Message")).toHaveValue("Create a card");
  expect(screen.queryByText("You")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
