// Consumed by the existing isolated S02 browser host, core and modeld fixture.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

module.exports = async function materialsJourney({ page, auId, origin, get, stats, check, until, host, hostLines, output }) {
  const before = (await stats()).inference_posts;
  const body = '业务资料：由三个模块组成，验收标识 u120-browser。';
  const name = '业务测试.md';
  const digest = crypto.createHash('sha256').update(body).digest('hex');
  const commands = [];
  const observe = request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands') commands.push(request.postDataJSON());
  };
  page.on('request', observe);
  const catalog = async () => (await get(page, '/api/v1/work/materials?organization_id=' + auId)).value;
  const workRead = async () => (await get(page, '/api/v1/work?organization_id=' + auId)).value;
  const workCommand = async (kind, data) => {
    const state = await workRead();
    const command = { id: crypto.randomUUID(), organization_id: auId, base_version: state.version, kind, data };
    const reply = await page.evaluate(async command => {
      const response = await fetch('/api/v1/work/commands', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(command)});
      return {status: response.status, value: await response.json()};
    }, command);
    assert.equal(reply.status, 200, JSON.stringify(reply.value)); assert.equal(reply.value.receipt.status, 'succeeded', reply.value.receipt.message);
    return {command, receipt: reply.value.receipt};
  };
  await page.goto(`${origin}/au/${auId}/resources`);
  const opener = page.getByRole('button', {name: '选择或粘贴业务资料', exact: true});
  await opener.waitFor();
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({width, height: 900});
    await opener.focus(); await page.keyboard.press('Enter');
    const dialog = page.locator('#material-dialog'); await dialog.waitFor();
    await dialog.getByLabel('业务资料正文', {exact: true}).fill(body);
    await dialog.getByRole('button', {name: '预览资料与授权', exact: true}).click();
    await dialog.getByRole('button', {name: '确认导入并授权只读', exact: true}).waitFor();
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press(i % 2 ? 'Shift+Tab' : 'Tab');
      assert.ok(await dialog.evaluate(el => el.contains(document.activeElement)));
    }
    check(`U120 preview, scope and keyboard fit ${width}px`, await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)
      && await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(output, `business-material-preview-${width}.png`), fullPage: true});
    await page.keyboard.press('Escape'); await dialog.waitFor({state: 'hidden'});
    check(`U120 closing clears draft and restores keyboard focus ${width}px`, await opener.evaluate(el => el === document.activeElement));
  }
  await page.setViewportSize({width: 1440, height: 1000});
  await opener.click();
  const dialog = page.locator('#material-dialog');
  await dialog.getByLabel('选择 UTF-8 文本文件', {exact: true}).setInputFiles({name, mimeType: 'text/markdown', buffer: Buffer.from(body)});
  await until(async () => await dialog.getByLabel('业务资料正文', {exact: true}).inputValue() === body, 'Business file did not decode');
  await dialog.getByRole('button', {name: '预览资料与授权', exact: true}).click();
  const confirm = dialog.getByRole('button', {name: '确认导入并授权只读', exact: true}); await confirm.waitFor();
  check('U120 preview performs zero inference and zero work commands', commands.length === 0 && (await stats()).inference_posts === before);
  await page.route('**/api/v1/work/commands', async route => {await route.fetch(); await route.abort('connectionreset');}, {times: 1});
  await confirm.click(); await dialog.getByRole('button', {name: '查询导入原请求', exact: true}).waitFor();
  await until(async () => commands.length === 1 && (await catalog()).materials.length === 1, 'Unknown import was not persisted');
  const imported = commands[0];
  const cached = await page.evaluate(() => JSON.stringify(sessionStorage));
  check('U120 unknown import stores only identity and digest, never body or filename', cached.includes(imported.id) && !cached.includes(body) && !cached.includes(name));
  await page.reload(); await opener.waitFor();
  host.stdin.write('{"op":"restart"}\n'); assert.equal((await hostLines()).restarted, true);
  await page.reload(); await opener.waitFor(); await opener.click();
  await page.locator('#material-dialog').getByRole('button', {name: '查询导入原请求', exact: true}).click();
  await page.getByText('资料已导入并授权本组织只读；未调用模型', {exact: true}).waitFor();
  await page.locator('#material-dialog').getByRole('button', {name: '返回资料列表', exact: true}).click();
  const material = (await catalog()).materials[0];
  check('U120 restart reopens the original import without replay or inference', commands.length === 1 && material.sha256 === digest
    && material.id === imported.data.material_id && material.source === 'file' && (await stats()).inference_posts === before);
  await page.getByRole('link', {name: '在工作中选择资料', exact: true}).click();
  await page.getByText('登记新的 AI 工作', {exact: true}).click();
  await page.getByLabel('工作标题', {exact: true}).fill('U120 同一工作读取资料');
  await page.getByLabel('目标', {exact: true}).fill('读取业务测试.md，归纳模块数。');
  await page.getByLabel('选择业务资料', {exact: true}).selectOption(`${material.id}:1`);
  const registration = page.getByRole('button', {name: '登记 AI 工作', exact: true}); await registration.click();
  await page.getByText('已登记有责任成员的工作；执行尚未开始', {exact: true}).waitFor();
  const workId = commands.at(-1).data.work_id;
  check('U120 work registration binds the chosen ID/version without inference', commands.at(-1).data.materials_root === material.id
    && commands.at(-1).data.material_version === 1 && (await stats()).inference_posts === before);
  await workCommand('start_attempt', {work_id: workId});
  const read = await workCommand('invoke_tool', {work_id: workId, tool: 'read_document', arguments: {path: name}});
  check('U120 explicit read proves digest and source without returning private body', read.receipt.result.sha256 === digest
    && !('text' in read.receipt.result) && read.receipt.tool_call.material_id === material.id);
  await workCommand('run_step', {work_id: workId});
  await workCommand('run_step', {work_id: workId});
  const observed = await stats();
  const tool = JSON.parse(observed.calls.at(-1).body.messages.findLast(message => message.role === 'tool').content);
  check('U120 actual core/modeld/SDK sends imported body only after the authorized tool read', observed.inference_posts === before + 2
    && !JSON.stringify(observed.calls.at(-2).body).includes(body) && tool.content === body && tool.sha256 === digest && observed.real_model_calls === 0);
  const work = (await workRead()).works.find(item => item.id === workId);
  check('U120 model result retains original tool provenance', work.tool_calls.some(call => call.material_id === material.id && call.sha256 === digest)
    && work.results.length === 1 && work.results[0].sources.some(source => work.tool_calls.some(call => call.step_ref === source)));
  await page.reload(); await page.getByRole('button', {name: '刷新工作资料依据', exact: true}).click();
  await page.getByText(/实际读取依据：业务测试.md/).first().waitFor();
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({width, height: 900});
    check(`U120 saved work and provenance fit ${width}px`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(output, `business-material-work-${width}.png`), fullPage: true});
  }
  await page.goto(`${origin}/au/${auId}/resources`); await opener.waitFor();
  const card = page.locator('.material-list li').filter({has: page.getByRole('heading', {name, exact: true})});
  await card.getByText('撤销这份资料的只读许可', {exact: true}).click();
  await card.getByLabel('撤销依据', {exact: true}).fill('受控验收结束，拒绝后续读取');
  await card.getByRole('button', {name: '确认撤销只读许可', exact: true}).click();
  await until(async () => !(await catalog()).materials[0].read_allowed, 'Material revocation was not persisted');
  const original = await get(page, '/api/v1/governance/receipts?' + new URLSearchParams({organization_id: auId, id: read.command.id}));
  check('U120 revoked original receipt retains the read fact without body disclosure', original.status === 200
    && original.value.receipt.tool_call.step_ref === read.receipt.tool_call.step_ref && !('text' in original.value.receipt.result));
  await page.goto(`${origin}/au/${auId}/work/${workId}`);
  await page.getByText('资料许可或准备条件需核对 · 0 份', {exact: true}).waitFor();
  check('U120 revoked binding remains on the original Work with no replacement or inference', (await workRead()).works[0].id === workId
    && (await stats()).inference_posts === before + 2);
  page.off('request', observe);
  fs.writeFileSync(path.join(output, 'business-materials.json'), JSON.stringify({scope: 'controlled browser/core HTTP/SQLite/modeld/SDK loopback',
    actual_model_calls: 0, bounded_inference_posts: 2, imported_material_digest: digest, observed_at: new Date().toISOString()}, null, 2));
};
