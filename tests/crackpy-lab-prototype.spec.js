const { test, expect } = require("@playwright/test");

const prototypePath = "/docs/inspection/crackpy-lab-prototype/index.html?debug=1";

test("CrackPy Lab prototype uses actual data and exposes test controls", async ({ page }) => {
  await page.goto(prototypePath);

  await expect(page.getByTestId("field-panel")).toBeVisible();
  await expect(page.getByTestId("frame-table-panel")).toContainText("Williams fit");
  await expect(page.getByTestId("source-evidence")).toContainText("results_auto_integral_probs.csv");
  await expect(page.getByTestId("source-evidence")).toContainText("separate Williams proof export");
  await expect(page.getByTestId("method-evidence")).toContainText("a_n");
  await expect(page.getByTestId("node-surface-matrix")).toContainText("ResultQuantity");
  await expect(page.getByTestId("graph-artifact-controls")).toContainText("Williams proof export");

  const graphOptions = await page.locator("#graphArtifactSelect option").allTextContents();
  expect(graphOptions.some((option) => option.includes("CJP"))).toBe(true);
  await page.locator("#graphArtifactSelect").selectOption("method-fit-cjp");
  await expect(page.getByTestId("source-evidence")).toContainText("_cjp_fit_graph.json");
  await expect(page.locator("#provenanceBadge")).toContainText("CJP fit");
  await expect(page.locator("#provenanceSnippet")).toContainText('"graph_artifact": "method-fit-cjp"');
  const cjpGraphState = await page.evaluate(() => window.CrackPyLabDebug.getState());
  expect(cjpGraphState.graphArtifactId).toBe("method-fit-cjp");
  expect(cjpGraphState.graphArtifactPath).toContain("_cjp_fit_graph.json");

  const initialState = await page.evaluate(() => window.CrackPyLabDebug.getState());
  expect(initialState.activeSources.nodemap).toContain("test_data/crack_detection/Nodemaps");

  await page.locator('[data-overlay="disp_y"]').click();
  await page.locator("#fieldColoring").selectOption("cividis");
  await expect(page.locator("#fieldCanvas")).toHaveAttribute("data-active-field", "disp_y");
  await expect(page.locator("#fieldCanvas")).toHaveAttribute("data-active-colormap", "cividis");

  await page.locator("#fieldScalePreset").selectOption("sigma2");
  let fieldState = await page.evaluate(() => window.CrackPyLabDebug.getState());
  expect(fieldState.fieldScalePreset).toBe("sigma2");
  expect(Number.isFinite(fieldState.fieldVmin)).toBe(true);
  expect(Number.isFinite(fieldState.fieldVmax)).toBe(true);

  await page.locator("#fieldSigma").fill("1.5");
  fieldState = await page.evaluate(() => window.CrackPyLabDebug.getState());
  expect(fieldState.fieldScalePreset).toBe("customSigma");
  expect(fieldState.fieldSigma).toBe(1.5);

  await page.locator("#fieldVmin").fill("-0.01");
  await page.locator("#fieldVmax").fill("0.02");
  fieldState = await page.evaluate(() => window.CrackPyLabDebug.getState());
  expect(fieldState.fieldScalePreset).toBe("manual");
  expect(fieldState.fieldVmin).toBeCloseTo(-0.01, 4);
  expect(fieldState.fieldVmax).toBeCloseTo(0.02, 4);

  const transformBefore = await page.locator("#fieldCanvas").evaluate((el) => getComputedStyle(el).transform);
  await page.locator("#fieldZoom").fill("2");
  const transformAfter = await page.locator("#fieldCanvas").evaluate((el) => getComputedStyle(el).transform);
  expect(transformBefore).not.toEqual(transformAfter);

  await page.locator("#setupOverlayMode").selectOption("annulus");
  await expect(page.locator('[data-feature="annulus-overlay"]')).toBeVisible();
  await expect(page.getByTestId("williams-fit-annulus").locator(".williams-annulus-domain")).toHaveAttribute("d", /A /);
  await expect(page.locator('[data-feature="line-integral-paths"]')).toHaveCount(0);

  await page.locator("#methodEvidenceMode").selectOption("pathStability");
  await expect(page.getByTestId("method-evidence")).toContainText("q10-q90");
  await page.locator("#methodEvidenceMode").selectOption("integralSummary");
  await expect(page.getByTestId("method-evidence")).toContainText("wo outliers");

  await page.evaluate(() => window.CrackPyLabDebug.setFeature("analysis-graph", false));
  await expect(page.getByTestId("analysis-graph")).toBeHidden();
  await page.evaluate(() => window.CrackPyLabDebug.resetFeatures());
  await expect(page.getByTestId("analysis-graph")).toBeVisible();

  await page.locator('[data-feature-toggle="method-evidence"]').uncheck();
  await expect(page.getByTestId("method-evidence")).toBeHidden();
  await page.locator('[data-feature-toggle="method-evidence"]').check();
  await expect(page.getByTestId("method-evidence")).toBeVisible();

  const assertionResults = await page.evaluate(() => window.CrackPyLabDebug.runAssertions());
  expect(assertionResults.every((result) => result.pass)).toBe(true);
  await expect(page.getByTestId("debug-assertion-status")).toContainText("PASS");
});

test("start experiment advances through real fixture frames", async ({ page }) => {
  await page.goto(prototypePath);

  const before = await page.evaluate(() => window.CrackPyLabDebug.getState());
  await page.getByRole("button", { name: "Start Experiment" }).click();
  await expect(page.locator("#runBadge")).toContainText("running");
  await expect.poll(async () => page.evaluate(() => window.CrackPyLabDebug.getState().frame), { timeout: 2000 }).not.toBe(before.frame);
  const after = await page.evaluate(() => window.CrackPyLabDebug.getState());

  expect(after.frame).not.toEqual(before.frame);
  expect(after.activeSources.resultCsv).toContain("results_auto_integral_probs.csv");
  await expect(page.locator("#provenanceSnippet")).toContainText(`"frame": ${after.frame}`);
});
