const { test, expect } = require("@playwright/test");
const { FIXTURE_FC, EMPTY_FC, mockDabsData } = require("./fixtures");

test.beforeEach(async ({ page }) => {
  await mockDabsData(page);
});

test.describe("initial render", () => {
  test("renders one list item per feature, sorted by validity start", async ({ page }) => {
    await page.goto("/web/index.html");
    const items = page.locator(".area-item");
    await expect(items).toHaveCount(FIXTURE_FC.features.length);
    await expect(items.nth(0)).toContainText("TEST1");
    await expect(items.nth(1)).toContainText("W5678/26");
  });

  test("shows the empty-state message when a day has no areas", async ({ page }) => {
    await mockDabsData(page, EMPTY_FC);
    await page.goto("/web/index.html");
    await expect(page.locator(".area-list-empty")).toBeVisible();
  });

  test("loads with no console errors", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/web/index.html");
    await page.waitForTimeout(500);
    expect(errors).toEqual([]);
  });
});

test.describe("area selection", () => {
  test("clicking a list item selects it and zooms the map to 7", async ({ page }) => {
    await page.goto("/web/index.html");
    await page.locator(".area-item").first().click();
    await expect(page.locator(".area-item.active")).toHaveCount(1);
    await expect(page.locator(".area-item").first()).toHaveClass(/active/);
    await expect.poll(() => page.evaluate(() => map.getZoom())).toBe(7);
  });

  test("arrow-key navigation wraps past the last item back to the first", async ({ page }) => {
    await page.goto("/web/index.html");
    await page.locator(".area-item").first().click();
    await page.keyboard.press("ArrowUp"); // from index 0 should wrap to the last item
    const lastId = await page.locator(".area-item-id").last().textContent();
    await expect(page.locator(".area-item.active .area-item-id")).toHaveText(lastId);
  });

  test("arrow-key navigation wraps past the first item back to the last", async ({ page }) => {
    await page.goto("/web/index.html");
    await page.locator(".area-item").last().click();
    await page.keyboard.press("ArrowDown"); // from the last index should wrap to 0
    const firstId = await page.locator(".area-item-id").first().textContent();
    await expect(page.locator(".area-item.active .area-item-id")).toHaveText(firstId);
  });

  test("rapid successive selections all reliably reach zoom 7", async ({ page }) => {
    // Regression test: flyTo/animated setView both proved unreliable under
    // back-to-back calls (see commit "Fix unreliable area-select zoom").
    await page.goto("/web/index.html");
    const items = page.locator(".area-item");
    const count = await items.count();
    for (let i = 0; i < count; i++) {
      await items.nth(i).click();
    }
    await expect.poll(() => page.evaluate(() => map.getZoom())).toBe(7);
  });
});

test.describe("date tabs", () => {
  test("switching tabs reloads the area list", async ({ page }) => {
    await page.goto("/web/index.html");
    await expect(page.locator(".area-item")).toHaveCount(FIXTURE_FC.features.length);
    await page.locator(".date-tab").nth(1).click();
    await expect(page.locator(".date-tab").nth(1)).toHaveClass(/active/);
    await expect(page.locator(".area-item")).toHaveCount(FIXTURE_FC.features.length);
  });

  test("tab dates are shown as DD.MM.YYYY", async ({ page }) => {
    await page.goto("/web/index.html");
    await expect(page.locator(".date-tab .ymd").first()).toHaveText(/^\d{2}\.\d{2}\.\d{4}$/);
  });
});

test.describe("language switching", () => {
  test("switching language translates the area list panel title", async ({ page }) => {
    await page.goto("/web/index.html");
    await page.locator('.lang-btn[data-lang="de"]').click();
    await expect(page.locator("#area-list-title")).toHaveText("Luftraumzonen");
    await page.locator('.lang-btn[data-lang="fr"]').click();
    await expect(page.locator("#area-list-title")).toHaveText("Zones aériennes");
  });

  test("the language dropdown stays in sync with the button switcher", async ({ page }) => {
    // #lang-select is only visible (and so only interactable) on mobile
    // widths - see the <=480px media query.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/web/index.html");
    await expect(page.locator("#lang-select")).toHaveValue("en");
    await page.locator("#lang-select").selectOption("de");
    await expect(page.locator("#area-list-title")).toHaveText("Luftraumzonen");
  });

  test("mobile viewport shows the language dropdown instead of the buttons", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/web/index.html");
    await expect(page.locator("#lang-select")).toBeVisible();
    await expect(page.locator(".lang-switch")).toBeHidden();
  });

  test("desktop viewport shows the language buttons instead of the dropdown", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/web/index.html");
    await expect(page.locator(".lang-switch")).toBeVisible();
    await expect(page.locator("#lang-select")).toBeHidden();
  });
});

test.describe("collapsible panels", () => {
  test("legend is collapsed by default and expands on click", async ({ page }) => {
    await page.goto("/web/index.html");
    const legend = page.locator("#legend");
    await expect(legend).not.toHaveJSProperty("open", true);
    await legend.locator("summary").click();
    await expect(legend).toHaveJSProperty("open", true);
  });

  test("disclaimer is collapsed by default and expands on click", async ({ page }) => {
    await page.goto("/web/index.html");
    const disclaimer = page.locator("#disclaimer");
    await expect(disclaimer).not.toHaveJSProperty("open", true);
    await disclaimer.locator("summary").click();
    await expect(disclaimer).toHaveJSProperty("open", true);
  });

  test("area list panel defaults open on a desktop-width viewport", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/web/index.html");
    await expect(page.locator("#area-list-panel")).toHaveJSProperty("open", true);
  });

  test("area list panel defaults collapsed on a mobile-width viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/web/index.html");
    await expect(page.locator("#area-list-panel")).toHaveJSProperty("open", false);
  });

  test("collapsing the area list panel on desktop gives its space back to the map", async ({ page }) => {
    // Regression test: the panel used to keep its full width/height even
    // collapsed, leaving a large empty void instead of growing the map.
    // Width is capped to never exceed the open width (the summary's
    // title+hint can legitimately need the full available width, so it's
    // bounded rather than strictly shrinking), height always shrinks since
    // the list itself disappears.
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/web/index.html");
    const panel = page.locator("#area-list-panel");
    const openBox = await panel.boundingBox();
    await panel.locator("summary").click();
    const closedBox = await panel.boundingBox();
    expect(closedBox.width).toBeLessThanOrEqual(openBox.width);
    expect(closedBox.height).toBeLessThan(openBox.height);
  });
});
