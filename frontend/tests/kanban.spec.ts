import { expect, test, type Locator, type Page } from "@playwright/test";
import type { BoardData } from "../src/lib/kanban";

test.skip(!process.env.PLAYWRIGHT_BASE_URL, "Requires FastAPI and SQLite");
let username: string;
const password = "part7-test-password";
test.beforeEach(async ({ page }) => {
  username = `p7_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const response = await page.request.post("/api/auth/register", { data: { username, password } });
  expect(response.ok()).toBe(true);
});

async function drag(page: Page, source: Locator, target: Locator) {
  await source.scrollIntoViewIfNeeded();
  // Wait for the previous sortable drop animation before measuring the next drag.
  await source.click({ trial: true });
  const from = await source.boundingBox();
  const to = await target.boundingBox();
  if (!from || !to) throw new Error("Missing drag coordinates");
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 8, from.y + from.height / 2, { steps: 3 });
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 15 });
  await page.mouse.up();
}

test("create, edit, cancel, rename, delete and retain changes across reload and login", async ({ page }) => {
  await page.goto("/");
  const column = page.getByTestId("column-col-backlog");
  await column.getByLabel("Column title").fill("Ideas");
  await column.getByText("Save column").click();
  await expect(column.getByText("Save column")).toHaveCount(0);
  await column.getByText("Add a card").click();
  await column.getByLabel("Card title").fill("Browser card");
  await column.getByLabel("Details").fill("Original details");
  await column.getByText("Add card", { exact: true }).click();
  await page.getByLabel("Edit Browser card", { exact: true }).click();
  await column.getByLabel("Card title").fill("Discarded draft");
  await column.getByText("Cancel", { exact: true }).click();
  await expect(page.getByText("Browser card", { exact: true })).toBeVisible();
  await page.getByLabel("Edit Browser card", { exact: true }).click();
  await column.getByLabel("Card title").fill("Edited browser card");
  await column.getByLabel("Details").fill("Saved details");
  await column.getByText("Save card").click();
  await expect(page.getByText("Saved details")).toBeVisible();
  await page.getByLabel("Delete Align roadmap themes", { exact: true }).click();
  await expect(page.getByText("Align roadmap themes", { exact: true })).toHaveCount(0);
  const saved: BoardData = await (await page.request.get("/api/board")).json();
  await page.reload();
  await expect(column.getByLabel("Column title")).toHaveValue("Ideas");
  await expect(page.getByText("Saved details")).toBeVisible();
  await page.getByText("Sign out", { exact: true }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByText("Sign in", { exact: true }).click();
  await expect(page.getByText("Saved details")).toBeVisible();
  expect(await (await page.request.get("/api/board")).json()).toEqual(saved);
});

test("reorders, moves across columns and drops into an empty column", async ({ page }) => {
  await page.setViewportSize({ width: 1500, height: 1100 });
  await page.goto("/");
  const backlog = page.getByTestId("column-col-backlog");
  const first = page.getByLabel("Move Align roadmap themes", { exact: true });
  await drag(page, first, page.getByLabel("Move Gather customer signals", { exact: true }));
  await expect(backlog.locator("article h4").first()).toHaveText("Gather customer signals");
  const review = page.getByTestId("column-col-review");
  await drag(page, first, page.getByLabel("Move QA micro-interactions", { exact: true }));
  await expect(review.getByText("Align roadmap themes", { exact: true })).toBeVisible();
  await page.getByLabel("Delete Prototype analytics view", { exact: true }).click();
  const discovery = page.getByTestId("column-col-discovery");
  await expect(discovery.getByText("Drop a card here")).toBeVisible();
  await drag(page, first, discovery.getByText("Drop a card here"));
  await expect(discovery.getByText("Align roadmap themes", { exact: true })).toBeVisible();
  await page.reload();
  await expect(discovery.getByText("Align roadmap themes", { exact: true })).toBeVisible();
});

test("expired sessions clear the board", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("column-col-backlog")).toBeVisible();
  await page.request.post("/api/auth/logout");
  await page.getByLabel("Delete Align roadmap themes", { exact: true }).click();
  await expect(page.getByLabel("Username")).toBeVisible();
  await expect(page.getByTestId("column-col-backlog")).toHaveCount(0);
  await expect(page.getByRole("alert").filter({ hasText: "Your session expired" })).toHaveText("Your session expired. Please sign in again.");
});

test("fits desktop and narrow layouts with editing controls and no browser errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  for (const width of [1500, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/");
    await page.getByLabel("Edit Align roadmap themes", { exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/part7-${width}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});

test("reorders cards with the keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 1500, height: 1100 });
  await page.goto("/");
  const handle = page.getByRole("button", { name: "Move Align roadmap themes", exact: true });
  await handle.focus();
  await page.keyboard.press("Space");
  await expect(handle).toHaveAttribute("aria-pressed", "true");
  // KeyboardSensor attaches its document listener on the next event-loop turn.
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await page.keyboard.press("ArrowDown");
  const targetId = (await page.getByRole("heading", { name: "Gather customer signals", exact: true }).locator("xpath=ancestor::article").getAttribute("data-testid"))!.slice(5);
  await expect(page.getByRole("status")).toContainText(`over droppable area ${targetId}`);
  await page.keyboard.press("Space");
  await expect(page.getByTestId("column-col-backlog").locator("article h4").first()).toHaveText("Gather customer signals");
});
