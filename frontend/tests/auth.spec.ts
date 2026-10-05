import { expect, test } from "@playwright/test";

test.skip(!process.env.PLAYWRIGHT_BASE_URL, "Requires the real FastAPI backend");

test("login, refresh, logout, and fresh sign-in preserve saved board state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in to Kanban Studio" })).toBeVisible();
  await expect(page.getByTestId("column-col-backlog")).toHaveCount(0);
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Invalid username or password." })).toBeVisible();
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio", exact: true })).toBeVisible();

  const cookies = await page.context().cookies();
  const session = cookies.find(cookie => cookie.name === "pm_session")!;
  expect(session.httpOnly).toBe(true);
  expect(session.sameSite).toBe("Strict");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByLabel("Password")).toHaveValue("");
  await expect(page.getByTestId("column-col-backlog")).toHaveCount(0);
  expect((await page.request.get("/api/auth/session")).status()).toBe(401);
  await page.reload();
  await expect(page.getByLabel("Username")).toBeVisible();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByTestId("column-col-backlog")).toBeVisible();
});

test("invalid cookie cannot reveal the board", async ({ page, baseURL }) => {
  await page.context().addCookies([{ name: "pm_session", value: "forged", url: baseURL! }]);
  await page.goto("/");
  await expect(page.getByLabel("Username")).toBeVisible();
  await expect(page.getByTestId("column-col-backlog")).toHaveCount(0);
});

test("login fits a narrow viewport and validates required fields", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Username")).toBeFocused();
  expect(await page.getByLabel("Username").evaluate((input: HTMLInputElement) => input.validity.valueMissing)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("registers an account, restores its identity, and rejects duplicates", async ({ page }) => {
  const username = `e2e_reg_${Date.now()}`;
  console.log(`Registration test account: ${username}`);
  await page.goto("/");
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("test-password-123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByText(`Signed in as ${username}`, { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText(`Signed in as ${username}`, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("test-password-123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByText("That username is already taken.")).toBeVisible();
  await page.getByRole("button", { name: "Already have an account? Sign in" }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password", { exact: true }).fill("test-password-123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText(`Signed in as ${username}`, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
});
