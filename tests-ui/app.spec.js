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

test.describe("validity time formatting", () => {
  test('a 23:59 UTC end time shows as 23:59 local, not rolled into the next day', async ({ page }) => {
    // Regression test: 23:59 UTC is DABS's "end of this day" sentinel, not a
    // real instant. Converting it faithfully to Swiss local time rolls it
    // into 01:59/00:59 the *next* calendar day, which reads as "valid into
    // tomorrow" even though the source means "until end of today".
    const fc = {
      type: "FeatureCollection",
      properties: { dabs_date: "2026-01-01", version: 1, generated_utc: "2026-01-01T10:00:00+00:00" },
      features: [
        {
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [[[7.0, 47.0], [7.01, 47.0], [7.01, 47.01], [7.0, 47.01], [7.0, 47.0]]] },
          properties: {
            id: "ENDOFDAY", notam: "ENDOFDAY", on_chart: true,
            valid_from_utc: "2026-01-01T05:00:00+00:00",
            valid_to_utc: "2026-01-01T23:59:00+00:00",
            lower: { raw: "GND", meters: 0, feet: 0, flight_level: null, gnd: true },
            upper: { raw: "1000m / 3281ft", meters: 1000, feet: 3281, flight_level: null, gnd: false },
            center: { lat: 47.005, lon: 7.005 }, radius_m: 500,
            radius_candidates_m: { table_km: 500 }, geometry_source: "circle",
            text: "TEST END OF DAY.",
          },
        },
      ],
    };
    await mockDabsData(page, fc);
    await page.goto("/web/index.html");
    const timeText = await page.locator(".area-item-time").first().textContent();
    expect(timeText).toContain("23:59");
    expect(timeText).not.toMatch(/0[01]:59/);
  });

  test('a 00:00 UTC start time shows as 00:00 local, not shifted into the prior evening', async ({ page }) => {
    // Regression test: 00:00 UTC is DABS's "start of this day" sentinel,
    // not a real instant. Converting it faithfully to Swiss local time
    // shifts it to 01:00/02:00 the *same* day, which is a smaller, less
    // obviously-wrong error than the 23:59 case, but still means "start of
    // day" (00:00) and "start of day plus the CH/UTC offset" display
    // differently.
    const fc = {
      type: "FeatureCollection",
      properties: { dabs_date: "2026-01-01", version: 1, generated_utc: "2026-01-01T10:00:00+00:00" },
      features: [
        {
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [[[7.0, 47.0], [7.01, 47.0], [7.01, 47.01], [7.0, 47.01], [7.0, 47.0]]] },
          properties: {
            id: "STARTOFDAY", notam: "STARTOFDAY", on_chart: true,
            valid_from_utc: "2026-01-01T00:00:00+00:00",
            valid_to_utc: "2026-01-01T10:00:00+00:00",
            lower: { raw: "GND", meters: 0, feet: 0, flight_level: null, gnd: true },
            upper: { raw: "1000m / 3281ft", meters: 1000, feet: 3281, flight_level: null, gnd: false },
            center: { lat: 47.005, lon: 7.005 }, radius_m: 500,
            radius_candidates_m: { table_km: 500 }, geometry_source: "circle",
            text: "TEST START OF DAY.",
          },
        },
      ],
    };
    await mockDabsData(page, fc);
    await page.goto("/web/index.html");
    const timeText = await page.locator(".area-item-time").first().textContent();
    expect(timeText).toMatch(/^00:00/);
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
    // Not a native <details> (see CLAUDE.md for why), so "open" is a plain
    // attribute set by hand in app.js, not a JS boolean property.
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/web/index.html");
    await expect(page.locator("#area-list-panel")).toHaveAttribute("open", "");
  });

  test("area list panel defaults collapsed on a mobile-width viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/web/index.html");
    await expect(page.locator("#area-list-panel")).not.toHaveAttribute("open");
  });

  test("area list panel is scrollable when its content overflows the collapsed height", async ({ page }) => {
    // Regression test: native <details> silently refused to let its content
    // shrink to a flex/grid max-height no matter the CSS, so overflow
    // content was clipped by the panel's own overflow:hidden with no way to
    // scroll to it - switched to a plain div for this reason (see
    // CLAUDE.md). Uses the real fixture's items stretched tall via inline
    // style, rather than depending on there being enough real features to
    // overflow on any given day.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/web/index.html");
    await page.locator("#area-list-toggle").click();
    await page.evaluate(() => {
      for (const li of document.querySelectorAll(".area-item")) li.style.height = "200px";
    });
    const list = page.locator("#area-list");
    const clientHeight = await list.evaluate((el) => el.clientHeight);
    const scrollHeight = await list.evaluate((el) => el.scrollHeight);
    expect(clientHeight).toBeLessThan(scrollHeight);
    await list.evaluate((el) => { el.scrollTop = 50; });
    await expect.poll(() => list.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
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
    await page.locator("#area-list-toggle").click();
    const closedBox = await panel.boundingBox();
    expect(closedBox.width).toBeLessThanOrEqual(openBox.width);
    expect(closedBox.height).toBeLessThan(openBox.height);
  });
});
