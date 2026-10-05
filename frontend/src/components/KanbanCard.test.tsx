import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DndContext } from "@dnd-kit/core";
import { SortableContext } from "@dnd-kit/sortable";
import { describe, expect, it, vi } from "vitest";
import type { Card } from "@/lib/kanban";
import { KanbanCard } from "./KanbanCard";

const renderCard = (card: Card, onEdit = vi.fn().mockResolvedValue(true)) => {
  const ui = (current: Card) => (
    <DndContext>
      <SortableContext items={[current.id]}>
        <KanbanCard card={current} disabled={false} onEdit={onEdit} onDelete={vi.fn()} />
      </SortableContext>
    </DndContext>
  );
  const view = render(ui(card));
  return { onEdit, update: (next: Card) => view.rerender(ui(next)) };
};

describe("KanbanCard", () => {
  it("saves edits normally when the card is unchanged", async () => {
    const { onEdit } = renderCard({ id: "c1", title: "Old", details: "Notes" });
    await userEvent.click(screen.getByLabelText("Edit Old"));
    await userEvent.clear(screen.getByLabelText("Card title"));
    await userEvent.type(screen.getByLabelText("Card title"), "Mine");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Save card"));
    expect(onEdit).toHaveBeenCalledWith("c1", "Mine", "Notes");
  });

  it("warns before overwriting a version saved while editing", async () => {
    const { onEdit, update } = renderCard({ id: "c1", title: "Old", details: "Notes" });
    await userEvent.click(screen.getByLabelText("Edit Old"));
    await userEvent.clear(screen.getByLabelText("Card title"));
    await userEvent.type(screen.getByLabelText("Card title"), "Mine");
    update({ id: "c1", title: "AI title", details: "AI notes" });
    expect(screen.getByRole("alert")).toHaveTextContent("AI title");
    expect(screen.getByLabelText("Card title")).toHaveValue("Mine");
    expect(screen.queryByText("Save card")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Overwrite changes"));
    expect(onEdit).toHaveBeenCalledWith("c1", "Mine", "Notes");
  });
});
