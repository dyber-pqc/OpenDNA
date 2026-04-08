import { test, expect } from "@playwright/test";

test("home page loads and shows header buttons", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("header")).toBeVisible();
  await expect(page.getByRole("button", { name: /Dashboard/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Academy/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Components/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Workflow/i })).toBeVisible();
});

test("component manager opens", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Components/i }).click();
  await expect(page.getByText(/Component Manager/i)).toBeVisible();
});

test("workflow editor opens", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Workflow/i }).click();
  await expect(page.getByText(/Visual Workflow Editor/i)).toBeVisible();
});
