/* Browser acceptance checks for the progress site; no model or deployment calls. */
const { chromium } = require(process.env.UNION_PLAYWRIGHT_MODULE || "playwright-core");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const output = path.join(root, "evidence", "site");
const base = process.env.UNION_SITE_TEST_URL || "http://127.0.0.1:8765";
const singleFile = process.env.UNION_SITE_SINGLE_FILE;
const prefix = singleFile ? "single-file-" : "";
const reportFile = singleFile ? "single-file-validation.json" : "browser-validation.json";
const csp = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'";

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.UNION_CHROMIUM_PATH || "/usr/bin/chromium" });
  const checks = [];
  const errors = [];
  const failures = [];
  const requests = [];
  const check = (name, value) => { assert.ok(value, name); checks.push(name); };
  const downloadText = async (page, selector) => {
    const pending = page.waitForEvent("download");
    await page.locator(selector).click();
    const download = await pending;
    assert.equal(await download.failure(), null);
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    return { name: download.suggestedFilename(), content: Buffer.concat(chunks).toString("utf8") };
  };
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("response", response => { if (response.status() >= 400) failures.push({ url: response.url(), status: response.status() }); });
    if (singleFile) {
      // Managed Chromium blocks file navigation. Exercise the exact HTML in a
      // disconnected browser document; keep that distinct from a file:// test.
      await context.setOffline(true);
      page.on("request", request => requests.push(request.url()));
      await page.route("**/*", route => route.abort());
      await page.setContent(fs.readFileSync(path.resolve(singleFile), "utf8"), { waitUntil: "load" });
      check("single HTML has no external resources", await page.locator("script[src], link[rel=stylesheet], img[src]:not([src^='data:'])").count() === 0);
      check("single HTML enforces inline hash CSP", (await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content")).includes("'sha256-"));
    } else {
      // Reproduce the Cloudflare _headers policy while using a local static server.
      await page.route("**/*", async route => {
        const response = await route.fetch();
        await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": csp } });
      });
      await page.goto(base, { waitUntil: "networkidle" });
    }
    await page.waitForFunction(() => document.getElementById("architecture-description").textContent.length > 10);
    check("mechanism test count comes from evidence", (await page.locator("#test-count").textContent()) === "25");
    check("real model count explicitly remains zero", (await page.locator("#real-count").textContent()) === "0");
    check("simulation label visible", await page.getByText("模拟重放 · 不调用模型").isVisible());
    check("twelve capabilities available", await page.locator("#capability-table tr").count() === 12);
    check("initial demo has no tasks", await page.getByText("尚未派发工作", { exact: true }).isVisible());
    check("previous button initially disabled", await page.locator("#demo-prev").isDisabled());
    await page.locator("#demo-next").click();
    check("bootstrap forms two members", await page.locator(".demo-member").count() === 2);
    check("dependency prevents premature delivery", (await page.locator(".work-row").nth(1).textContent()).includes("等待依赖"));
    await page.locator("#demo-next").click();
    check("first delivery is visible", await page.locator(".work-row.completed").count() === 1);
    await page.locator("#demo-next").click();
    check("cross-member collaboration delivered two tasks", await page.locator(".work-row.completed").count() === 2);
    await page.locator(".demo-shell").screenshot({ path: path.join(output, prefix + "demo.png") });
    await page.locator("#demo-next").click();
    check("next decision adds followup task", await page.locator(".work-row").count() === 3);
    await page.locator("#demo-next").click();
    check("followup task actually appears delivered", await page.locator(".work-row.completed").count() === 3);
    await page.locator("#demo-next").click();
    check("finished replay enters persistent wait", (await page.locator("#inspector-phase").textContent()) === "等待新事件");
    check("six fixture calls recorded separately", (await page.locator("#inspector-calls").textContent()) === "6");
    check("next button disabled at terminal stage", await page.locator("#demo-next").isDisabled());
    await page.locator("#demo-reset").click();
    check("reset clears simulated work", await page.locator(".work-row").count() === 0);
    await page.locator("#demo-play").click();
    await page.waitForFunction(() => document.getElementById("inspector-calls").textContent === "1");
    await page.locator("#demo-play").click();
    await page.waitForTimeout(1650);
    check("pause stops automatic replay", (await page.locator("#inspector-calls").textContent()) === "1");
    await page.locator("#demo-reset").click();
    await page.getByRole("button", { name: "查看阶段 4：成果触发下一轮决定", exact: true }).click();
    check("timeline can jump to a specific stage", (await page.locator("#inspector-version").textContent()) === "v6");
    await page.locator("#view-artifacts").click();
    check("artifact modal opens", await page.locator("#artifact-dialog").isVisible());
    check("first artifact is explicitly simulated", (await page.locator("#artifact-content").textContent()).includes("模拟资料"));
    await page.getByRole("button", { name: "followup.md", exact: true }).click();
    check("artifact tab changes actual content", (await page.locator("#artifact-content").textContent()).includes("模拟后续动作"));
    for (const name of ["source.md", "dependent.md", "followup.md"]) {
      await page.getByRole("button", { name, exact: true }).click();
      const download = await downloadText(page, "#artifact-download");
      check("embedded artifact download: " + name, download.name === name && download.content === await page.locator("#artifact-content").textContent());
    }
    await page.keyboard.press("Escape");
    check("escape closes native dialog", !(await page.locator("#artifact-dialog").isVisible()));
    for (const [key, title] of Object.entries({ governance: "授权与章程", runtime: "组织循环", executor: "成员执行器", context: "上下文与记忆", state: "持久化状态", artifacts: "版本化成果" })) {
      await page.locator(`[data-node="${key}"]`).click();
      check("architecture node: " + key, (await page.locator("#architecture-name").textContent()) === title && await page.locator('[data-node][aria-pressed="true"]').count() === 1);
    }
    await page.locator('[data-node="governance"]').focus();
    await page.keyboard.press("Enter");
    check("architecture supports keyboard activation", (await page.locator("#architecture-name").textContent()) === "授权与章程");
    await page.locator('[data-node="runtime"]').click();
    const publicData = await downloadText(page, "#report-download");
    const snapshot = JSON.parse(publicData.content);
    check("embedded validation summary downloads intact", publicData.name === "ai-union-validation.json" && JSON.stringify(snapshot) === await page.evaluate(() => JSON.stringify(window.UNION_DATA)));
    check("public evidence retains unverified outcomes", snapshot.verification.real_agent_verified === false && snapshot.verification.external_market_feedback_verified === false);
    await page.locator("#demo-reset").click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, prefix + "desktop.png"), fullPage: true });
    for (const width of [1440, 800, 390, 320]) {
      await page.setViewportSize({ width, height: 950 });
      await page.waitForTimeout(80);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      check("no horizontal overflow at " + width + "px", !overflow);
      if (width === 390) await page.screenshot({ path: path.join(output, prefix + "mobile.png"), fullPage: true });
    }
    check("no JavaScript or CSP console errors", errors.length === 0);
    check("no failed browser resource requests", failures.length === 0);
    if (singleFile) check("all interactions and downloads work without network requests", requests.length === 0);
    fs.writeFileSync(path.join(output, reportFile), JSON.stringify({ status: "passed", checked_at: new Date().toISOString(), browser: await browser.version(), checks, errors, failures, requests: singleFile ? requests : undefined, mode: singleFile ? "offline browser document (setContent)" : "static HTTP", direct_file_navigation_verified: false, real_model_calls: 0, csp_applied: true }, null, 2));
    console.log(`${checks.length} browser checks passed; desktop, mobile and demo screenshots saved`);
  } catch (error) {
    fs.writeFileSync(path.join(output, reportFile), JSON.stringify({ status: "failed", checks, error: error.message, errors, failures, requests }, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
