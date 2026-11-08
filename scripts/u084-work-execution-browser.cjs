// Full React + authenticated HTTP + SQLite. Zero real model/provider calls.
const { chromium } = require("playwright-core");
const { spawn } = require("node:child_process");
const { createInterface } = require("node:readline");
const path = require("node:path");
const fs = require("node:fs");
const assert = require("node:assert/strict");

async function main() {
  const pendingReceipt = process.env.UNION_U084_PENDING_RECEIPT === "1";
  const readOnlyReceipt = process.env.UNION_U084_READ_ONLY_RECEIPT === "1";
  const host = spawn(
    process.env.UNION_PYTHON || "python3",
    [path.join(__dirname, "u084_work_execution_host.py"), ...(pendingReceipt ? ["--pending-receipt"] : [])],
    {
      cwd: path.join(__dirname, ".."),
      stdio: ["pipe", "pipe", "inherit"],
    },
  );
  let browser;
  try {
    const ready = await new Promise((resolve, reject) => {
      const lines = createInterface({ input: host.stdout });
      const timeout = setTimeout(
        () => reject(Error("U084 host not ready")),
        30000,
      );
      lines.once("line", (line) => {
        clearTimeout(timeout);
        resolve(JSON.parse(line));
      });
      host.once("error", reject);
      host.once("exit", (code) => {
        clearTimeout(timeout);
        reject(Error("Host exited " + code));
      });
    });
    browser = await chromium.launch({
      headless: true,
      ...(process.env.UNION_CHROMIUM_PATH
        ? { executablePath: process.env.UNION_CHROMIUM_PATH }
        : {}),
    });
    const context = await browser.newContext();
    await context.addCookies([
      {
        name: ready.cookie_name,
        value: ready.token,
        url: ready.origin,
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
    const page = await context.newPage();
    let posts = 0,
      original;
    let confirmCommit, commandError;
    const committed = new Promise((resolve) => {
      confirmCommit = resolve;
    });
    await page.route("**/api/v1/work/commands", async (route) => {
      try {
        posts++;
        original = route.request().postDataJSON();
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        const ack = await response.json();
        assert.equal(ack.receipt.status, "succeeded");
        assert.equal(ack.receipt.result, true);
        // Lose only the response after the actual command commits. Never post again.
        await route.abort("failed");
      } catch (error) {
        commandError = error;
      } finally {
        confirmCommit();
      }
    });
    await page.goto(
      ready.origin +
        "/tasks?organization=" +
        encodeURIComponent(ready.organization_id),
    );
    const run = page.getByRole("button", { name: "运行 AI 工作", exact: true });
    await run.click();
    await page.getByText(/原请求已保留/).waitFor();
    if (pendingReceipt) {
      const lookup = page.getByRole("button", { name: "查询原请求", exact: true });
      const unavailable = page.waitForResponse((r) => r.url().includes("/api/v1/governance/receipts?"));
      await lookup.click();
      assert.equal((await unavailable).status(), 403);
      const feedback = page.getByText(/原回执尚不可取得|权限或身份已变化/);
      await feedback.waitFor({ timeout: 3000 });
      assert.match(await feedback.textContent(), /原回执尚不可取得/);
      assert.equal(await lookup.isEnabled(), true);
      assert.equal(await page.getByRole("list", { name: "V1 工作列表", exact: true }).count(), 1);
      assert.equal(posts, 1);
      host.stdin.write("complete\n");
    }
    await committed;
    if (commandError) throw commandError;
    if (readOnlyReceipt) {
      const models = await (await context.request.get(ready.origin + "/api/v1/models?organization_id=" +
        encodeURIComponent(ready.organization_id))).json();
      const connection = models.connections.find(item => item.id === "connection-a");
      const disabled = await context.request.post(ready.origin + "/api/v1/models/commands", {
        headers: { Origin: ready.origin },
        data: { id: require("node:crypto").randomUUID(), organization_id: ready.organization_id,
          base_version: models.version, kind: "set_connection", data: {
            connection_id: connection.id, expected_revision: connection.revision,
            enabled: false, make_default: false } },
      });
      assert.equal(disabled.status(), 200);
      assert.equal((await disabled.json()).receipt.status, "succeeded");
      const work = await (await context.request.get(ready.origin + "/api/v1/work?organization_id=" +
        encodeURIComponent(ready.organization_id))).json();
      assert.equal(work.access.can_start, false);
      assert.equal(work.works.length, 1);
    }
    await page.reload();
    const recoveredLookup = page.getByRole("button", { name: "查询原请求", exact: true });
    await recoveredLookup.waitFor({ timeout: 3000 });
    await recoveredLookup.click();
    await page.getByText(/本次操作已记录/).waitFor();
    assert.equal(posts, 1);
    assert.equal(original.kind, "run_loop");
    assert.equal(
      await page
        .getByRole("button", { name: "运行 AI 工作", exact: true })
        .count(),
      0,
    );
    const link = page
      .getByRole("list", { name: "V1 工作列表", exact: true })
      .getByRole("link", { name: "下载", exact: true });
    await link.waitFor();
    const download = await context.request.get(
      new URL(await link.getAttribute("href"), ready.origin).href,
    );
    assert.equal(download.status(), 200);
    assert.match(await download.text(), /U084 controlled result/);
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        "overflow " + width,
      );
    }
    const output = path.resolve(
      process.env.UNION_U084_EVIDENCE || ".union/u084-page-execution",
    );
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(
      path.join(output, "checks.json"),
      JSON.stringify(
        {
          scope: "controlled",
          original_id: original.id,
          work_posts: posts,
          checks: [
            ...(pendingReceipt ? ["pending receipt 403 preserves authorized work and original lookup"] : []),
            ...(readOnlyReceipt ? ["disabled execution preserves readable original lookup after reload"] : []),
            "actual run_loop over HTTP",
            "response lost after commit",
            "reload preserves original ID",
            "original receipt GET without replay",
            "persisted result download",
            "three viewport widths",
          ],
          real_model_calls: 0,
        },
        null,
        2,
      ) + "\n",
    );
    console.log(
      `U084 browser: ${6 + Number(pendingReceipt) + Number(readOnlyReceipt)} checks passed; one original POST, zero real model calls`,
    );
  } finally {
    host.stdin.end();
    if (browser) await browser.close();
    if (host.exitCode === null && host.signalCode === null)
      await new Promise((r) => host.once("exit", r));
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
