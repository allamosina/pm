import { describe, expect, it } from "vitest";
import { moveCard, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });

  it("moves into an empty column without mutating the input", () => {
    const columns = [...baseColumns, { id: "empty", title: "Empty", cardIds: [] }];
    const before = structuredClone(columns);
    const result = moveCard(columns, "card-1", "empty");
    expect(result.map(column => column.cardIds)).toEqual([["card-2"], ["card-3"], ["card-1"]]);
    expect(columns).toEqual(before);
    expect(result.flatMap(column => column.cardIds).sort()).toEqual(["card-1", "card-2", "card-3"]);
  });

  it("appends within the same column", () => {
    expect(moveCard(baseColumns, "card-1", "col-a")[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it.each([["unknown", "col-b"], ["card-1", "unknown"], ["card-1", "card-1"]])(
    "leaves the board unchanged for %s over %s", (active, over) => {
      expect(moveCard(baseColumns, active, over)).toBe(baseColumns);
    }
  );

});
