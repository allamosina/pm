import { expect, test } from "@playwright/test";

test.skip(!process.env.CHAT_MOCK_BACKEND, "Requires isolated backend/tests/browser_app.py");
test("AI batches refresh the board, retain failed drafts and reset history", async ({ page }) => {
  const username = `chat_${Date.now()}`;
  await page.request.post("/api/auth/register", { data: { username, password: "test-password-123" } });
  await page.goto("/");
  const message = page.getByLabel("Message", { exact: true });
  const send = page.getByRole("button", { name: "Send message" });
  await message.fill("Create two cards");
  await send.click();
  await expect(page.getByRole("heading", { name: "AI One", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "AI Two", exact: true })).toBeVisible();
  await message.fill("Edit and move it");
  await send.click();
  await expect(page.getByTestId("column-col-done").getByRole("heading", { name: "AI Edited" })).toBeVisible();
  await message.fill("Fail safely");
  await send.click();
  await expect(page.getByRole("alert").filter({ hasText: "AI request failed" })).toBeVisible();
  await expect(message).toHaveValue("Fail safely");
  await expect(page.getByRole("log")).not.toContainText("Fail safely");
  await message.fill("How many columns?");
  await send.click();
  await expect(page.getByRole("log")).toContainText("Your board has five columns.");
  await page.reload();
  await expect(page.getByRole("log")).not.toContainText("Created two cards.");
  await expect(page.getByRole("heading", { name: "AI Edited" })).toBeVisible();
  await message.fill("How many columns?");
  await send.click();
  await expect(page.getByRole("log")).toContainText("Your board has five columns.");
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("test-password-123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("log")).not.toContainText("Your board has five columns.");
  for (const width of [1500, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await message.scrollIntoViewIfNeeded();
    await message.focus();
    await expect(message).toBeFocused();
    await message.fill("How many columns?");
    await page.keyboard.press("Tab");
    await expect(send).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(message).toHaveValue("");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/part10-${width}.png`, fullPage: true });
  }
});
