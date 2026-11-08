// Actual Core page + HTTP + SQLite; the modeld endpoint is a loopback double.
const { chromium } = require('playwright-core');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

async function main() {
  const loseCancel = process.env.UNION_U086_LOSE_CANCEL === '1';
  const host = spawn(process.env.UNION_PYTHON || 'python3',
    [path.join(__dirname, 'u086_cancel_recovery_host.py')],
    { cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'inherit'] });
  const lines = createInterface({ input: host.stdout });
  const queue = [], readers = [];
  let exited = false;
  lines.on('line', line => {
    const value = JSON.parse(line);
    const reader = readers.shift();
    if (reader) reader.resolve(value); else queue.push(value);
  });
  host.once('exit', code => {
    exited = true;
    readers.splice(0).forEach(r => r.reject(Error('fixture exited ' + code)));
  });
  function next() {
    if (queue.length) return Promise.resolve(queue.shift());
    if (exited) return Promise.reject(Error('fixture already exited'));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('fixture response timeout')), 30000);
      readers.push({ resolve: value => { clearTimeout(timer); resolve(value); },
        reject: error => { clearTimeout(timer); reject(error); } });
    });
  }
  async function control(value) { host.stdin.write(value + '\n'); return next(); }
  let browser, releaseCancel;
  const heldCancel = new Promise(resolve => { releaseCancel = resolve; });
  try {
    let ready = await next();
    browser = await chromium.launch({ headless: true,
      ...(process.env.UNION_CHROMIUM_PATH ? { executablePath: process.env.UNION_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext();
    async function cookie() {
      await context.addCookies([{ name: ready.cookie_name, value: ready.token,
        url: ready.origin, httpOnly: true, sameSite: 'Lax' }]);
    }
    await cookie();
    const page = await context.newPage();
    page.setDefaultTimeout(8000);
    const posts = [];
    let cancelPostReceipt, routeError;
    await page.route('**/api/v1/work/commands', async route => {
      const request = route.request().postDataJSON(); posts.push(request);
      try {
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        const value = await response.json();
        assert.equal(value.receipt.kind, request.kind);
        if (request.kind === 'cancel_step') {
          cancelPostReceipt = value.receipt;
          assert.equal(value.receipt.status, 'succeeded');
          if (loseCancel) {
            await heldCancel; // Original GET confirms before the delayed POST fails.
            return await route.abort('failed');
          }
        }
        await route.fulfill({ response });
      } catch (error) { routeError = error; await route.abort('failed').catch(() => {}); }
    });
    const url = () => ready.origin + '/tasks?organization=' + encodeURIComponent(ready.organization_id);
    await page.goto(url());
    await page.getByRole('button', { name: '运行 AI 工作', exact: true }).click();
    await page.getByRole('group', { name: '原运行请求', exact: true }).waitFor();
    const workUrl = () => ready.origin + '/api/v1/work?organization_id=' + encodeURIComponent(ready.organization_id);
    let work;
    const reservationDeadline = Date.now() + 10000;
    do {
      const response = await context.request.get(workUrl()); assert.equal(response.status(), 200);
      work = (await response.json()).works[0];
      if (work.steps[0]?.status === 'reserved') break;
      await page.waitForTimeout(50);
    } while (Date.now() < reservationDeadline);
    assert.equal(work.steps[0]?.status, 'reserved', 'fixture must reach the original reservation');
    // An explicit read observes the original committed reservation while POST is pending.
    await page.getByRole('button', { name: '刷新 AI 工作', exact: true }).click();
    const cancel = page.getByRole('button', { name: '取消本次执行', exact: true });
    await cancel.waitFor();
    const disabled = await control('disable');
    assert.equal(disabled.access.can_start, false);
    assert.equal(disabled.works[0].steps[0].status, 'reserved');
    // The rendered button is now stale; fresh eligibility must prevent POST without losing GET.
    await cancel.click();
    await page.getByText('当前不能执行新操作；已有工作和原请求仍可查询，请核对模型连接及当前授权。').waitFor();
    const runGroup = page.getByRole('group', { name: '原运行请求', exact: true });
    assert.ok((await runGroup.textContent()).includes(posts[0].id));
    await runGroup.getByRole('button', { name: '查询原请求', exact: true }).click();
    await page.waitForFunction(() => Array.from(document.querySelectorAll('button'))
      .filter(b => b.textContent === '查询原请求').every(b => !b.disabled));
    assert.equal(posts.length, 1, 'eligibility refusal and lookup cannot POST');
    assert.equal((await control('inspect')).cancel_posts, 0);
    await control('enable');
    await page.getByRole('button', { name: '刷新 AI 工作', exact: true }).click();
    await cancel.click();
    await page.getByRole('group', { name: '原取消请求', exact: true }).waitFor();
    const cancelResponse = () => cancelPostReceipt || routeError;
    const deadline = Date.now() + 8000;
    while (!cancelResponse() && Date.now() < deadline) await page.waitForTimeout(50);
    if (routeError) throw routeError;
    assert.ok(cancelPostReceipt, 'actual cancel POST must complete');
    assert.equal(cancelPostReceipt.cancel_accepted, true, 'the original endpoint must accept this fixture cancellation');
    if (loseCancel) {
      const group = page.getByRole('group', { name: '原取消请求', exact: true });
      await group.getByRole('button', { name: '查询原请求', exact: true }).click();
      await group.getByText(/本次操作已记录/).waitFor();
      const confirmed = await page.getByRole('status').textContent();
      const failed = page.waitForEvent('requestfailed', request => request.url().endsWith('/api/v1/work/commands') &&
        request.postDataJSON().kind === 'cancel_step');
      releaseCancel(); await failed;
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert.equal(await page.getByRole('status').textContent(), confirmed,
        'late cancelled POST transport error must retain the confirmed original receipt');
    }
    if (!loseCancel) await page.getByRole('group', { name: '原取消请求', exact: true })
      .getByText(/本次操作已记录/).waitFor();
    assert.deepEqual(posts.map(p => p.kind), ['run_loop', 'cancel_step']);
    const [run, cancelled] = posts;
    assert.notEqual(run.id, cancelled.id);
    const before = await control('inspect');
    assert.equal(before.fake_model_calls, 1);
    assert.equal(before.cancel_posts, 1);
    assert.deepEqual(before.loop_command_ids, [run.id]);
    assert.equal(before.steps[0].command_id, run.id + '-t1');
    assert.equal(before.steps[0].status, 'reserved');
    assert.equal(await cancel.isEnabled(), false);
    await control('finish');
    const limit = Date.now() + 10000;
    do {
      const response = await context.request.get(workUrl()); assert.equal(response.status(), 200);
      work = (await response.json()).works[0];
      if (work.steps[0]?.status === 'unknown') break;
      await page.waitForTimeout(50);
    } while (Date.now() < limit);
    assert.equal(work.steps[0].status, 'unknown');
    assert.equal(work.budget.reserved, 1);
    await page.reload();
    for (const [name, original] of [['原运行请求', run], ['原取消请求', cancelled]]) {
      const group = page.getByRole('group', { name, exact: true });
      await group.waitFor(); assert.match(await group.textContent(), new RegExp(original.id));
      const response = page.waitForResponse(r => r.url().includes('/api/v1/governance/receipts?') &&
        new URL(r.url()).searchParams.get('id') === original.id);
      await group.getByRole('button', { name: '查询原请求', exact: true }).click();
      const r = await response; assert.equal(r.status(), 200);
      const value = (await r.json()).receipt;
      assert.equal(value.id, original.id); assert.equal(value.kind, original.kind);
      assert.equal(value.organization_id, ready.organization_id);
      if (original.kind === 'cancel_step') assert.deepEqual(value, cancelPostReceipt,
        'original cancellation GET must preserve the complete POST receipt');
      await group.getByRole('button').waitFor();
      // Receipt content adoption includes a subsequent session read.
      await page.waitForFunction(() => Array.from(document.querySelectorAll('button'))
        .filter(b => b.textContent === '查询原请求').every(b => !b.disabled));
    }
    const confirmedNote = await page.getByRole('status').textContent();
    await page.route('**/api/v1/governance/receipts?**', route => route.abort('failed'));
    const unavailable = page.waitForEvent('requestfailed', request => request.url().includes('/api/v1/governance/receipts?'));
    await page.getByRole('group', { name: '原取消请求', exact: true }).getByRole('button').click();
    await unavailable;
    await page.waitForFunction(() => Array.from(document.querySelectorAll('button'))
      .filter(b => b.textContent === '查询原请求').every(b => !b.disabled));
    assert.equal(await page.getByRole('status').textContent(), confirmedNote,
      'ordinary GET failure must retain a confirmed receipt');
    await page.unroute('**/api/v1/governance/receipts?**');
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'overflow ' + width);
    }
    const after = await control('inspect');
    ready = await control('reopen'); await cookie(); await page.goto(url());
    // Host service_instance changes: old browser references must not cross the new scope.
    assert.equal(await page.getByRole('group', { name: '原取消请求', exact: true }).count(), 0);
    const persisted = await context.request.get(ready.origin + '/api/v1/governance/receipts?organization_id=' +
      encodeURIComponent(ready.organization_id) + '&id=' + encodeURIComponent(cancelled.id));
    assert.equal(persisted.status(), 200);
    const storedCancel = (await persisted.json()).receipt;
    assert.equal(storedCancel.id, cancelled.id);
    assert.equal(storedCancel.kind, 'cancel_step');
    assert.deepEqual(storedCancel, cancelPostReceipt,
      'original cancellation receipt must remain identical after service restart');
    assert.equal(posts.length, 2);
    assert.equal(after.fake_model_calls, 1); assert.equal(after.cancel_posts, 1);
    assert.equal(after.steps[0].status, 'unknown');
    const checks = ['page sends cancel while original run POST is pending', 'separate original IDs',
      'actual HTTP cancel reaches original model request and AU', 'SQLite retains original run reservation',
      'cancel cannot be posted twice', 'both original GETs survive reload',
      'unknown retains one reservation', 'three viewport widths',
      'host restart preserves original cancellation receipt', 'new service scope excludes old browser references',
      'cancel POST and original GET contain the same complete accepted receipt',
      'restarted original GET contains the same complete accepted receipt',
      'real disabled default refuses stale cancel while preserving original run lookup',
      'eligibility refusal and original lookup produce zero additional POSTs',
      'ordinary GET failure retains confirmed cancellation'];
    if (loseCancel) checks.push('confirmed original cancellation survives its late failed POST');
    const output = path.resolve(process.env.UNION_U086_EVIDENCE || '.union/u086-cancel-recovery');
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify({ scope: 'controlled', checks,
      lose_cancel_response: loseCancel, work_posts: 2, fake_model_calls: 1, cancel_posts: 1, real_model_calls: 0,
      cancellation_receipt: { post_cancel_accepted: cancelPostReceipt.cancel_accepted,
        stored_cancel_accepted: storedCancel.cancel_accepted,
        complete_receipt_equal: true,
        note: 'Only receipt persistence is verified here; pre-delivery commit, unlocked I/O and response identity remain separate author-owned faults.' }
    }, null, 2) + '\n');
    console.log(`U086 page recovery: ${checks.length} checks passed; command POST=2, fake=1, real=0; lost cancel=${loseCancel}`);
  } finally {
    releaseCancel();
    if (!exited) host.stdin.write('finish\n');
    if (browser) await browser.close();
    host.stdin.end();
    if (!exited) await new Promise(resolve => host.once('exit', resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
