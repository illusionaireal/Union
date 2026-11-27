// Uses the existing isolated S02 host: actual React/HTTP/SQLite and controlled modeld/SDK.
// No real provider or native-profile new-input capability is claimed.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

module.exports = async function inputJourney({page, auId, origin, get, stats, check, until, host, hostLines, output}) {
  const before = (await stats()).inference_posts;
  const originalAU = await get(page, '/api/v1/aus/' + auId);
  assert.equal(originalAU.status, 200);
  const originalSchema = originalAU.value.au.schema_version;
  const commands = [];
  const observe = request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands') commands.push(request.postDataJSON());
  };
  page.on('request', observe);
  const read = async () => (await get(page, '/api/v1/work?organization_id=' + auId)).value;
  const command = async (kind, data) => {
    const state = await read();
    const reply = await page.evaluate(async body => {
      const response = await fetch('/api/v1/work/commands', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)});
      return {status: response.status, value: await response.json()};
    }, {id: crypto.randomUUID(), organization_id: auId, base_version: state.version, kind, data});
    assert.equal(reply.status, 200, reply.value.error); assert.equal(reply.value.receipt.status, 'succeeded', reply.value.receipt.message);
    return reply.value.receipt;
  };
  const models = (await get(page, '/api/v1/models?organization_id=' + auId)).value;
  const connection = models.connections.find(c => c.is_default);
  assert.ok(connection, 'U093 requires the existing authorized default connection');
  const materialId = 'material-' + crypto.randomUUID().replaceAll('-', ''), workId = 'u093-original-work';
  const first = 'U093 第一条补充：保留原来源\n<script>window.u093Executed=true</script>';
  const second = 'U093 第二条补充：原步骤之间按序采用';
  const pending = 'U093 后到要求：预算已用尽，保持待采用';
  await command('import_material', {material_id: materialId, name: '业务测试.md', content: 'U093 受控原工作资料', source: 'paste', reason: '受控输入边界验收'});
  await command('start_work', {work_id: workId, title: 'U093 原工作补充要求', goal: '读取业务测试.md，保留实际来源',
    member_name: '受控责任成员', member_id: 'u093-member', binding_id: 'u093-binding', mandate_id: 'u093-mandate', definition_id: 'u093-definition',
    connection_id: connection.id, expected_revision: connection.revision, materials_root: materialId, material_version: 1,
    max_calls: 2, tools: ['read_document'], reason: '受控原工作两轮，不调用真实模型'});
  await command('start_attempt', {work_id: workId});
  await page.goto(`${origin}/au/${auId}/work/${workId}`);
  const region = page.getByRole('region', {name: '原工作补充输入', exact: true});
  const body = region.getByLabel('补充输入正文', {exact: true}); await body.waitFor();
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({width, height: 900});
    await body.fill(first); await region.getByLabel('补充依据', {exact: true}).fill('受控补充，保留原责任');
    await body.focus(); await page.keyboard.press('Tab');
    check(`U093 input keyboard and layout fit ${width}px`, await region.getByLabel('补充依据', {exact: true}).evaluate(el => el === document.activeElement)
      && await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(output, `u093-input-${width}.png`), fullPage: true});
  }
  const submit = region.getByRole('button', {name: '收存补充输入', exact: true});
  await page.route('**/api/v1/work/commands', async route => {
    assert.equal(route.request().postDataJSON().kind, 'append_work_input'); await route.fetch(); await route.abort('connectionreset');
  }, {times: 1});
  await submit.focus(); await page.keyboard.press('Enter');
  await region.getByRole('button', {name: '查询输入原请求', exact: true}).waitFor();
  await until(async () => commands.some(c => c.kind === 'append_work_input') && (await read()).works.find(w => w.id === workId).inputs.length === 1,
    'U093 lost-response input did not persist');
  const original = commands.find(c => c.kind === 'append_work_input');
  check('U093 original Work receives one frozen scoped input without inference', Object.keys(original).length === 5
    && Object.keys(original.data).length === 4 && original.data.work_id === workId && /^input-[a-f0-9]{32}$/.test(original.data.input_id)
    && original.data.content === first && (await stats()).inference_posts === before);
  const cache = await page.evaluate(() => JSON.stringify({session: sessionStorage, local: localStorage}));
  check('U093 browser storage retains only original input identity and digest', cache.includes(original.id)
    && cache.includes(crypto.createHash('sha256').update(first).digest('hex')) && !cache.includes(first) && !cache.includes('受控补充，保留原责任'));
  host.stdin.write('{"op":"restart"}\n'); assert.equal((await hostLines()).restarted, true);
  await page.reload(); await region.getByRole('button', {name: '查询输入原请求', exact: true}).click();
  await until(async () => await region.getByRole('button', {name: '继续补充输入', exact: true}).isVisible(), 'U093 original input query did not resolve');
  const receipt = await get(page, '/api/v1/governance/receipts?' + new URLSearchParams({organization_id: auId, id: original.id}));
  check('U093 restart queries original receipt without rePOST or model dispatch', receipt.status === 200 && receipt.value.receipt.status === 'succeeded'
    && receipt.value.receipt.input.id === original.data.input_id && commands.filter(c => c.kind === 'append_work_input').length === 1 && (await stats()).inference_posts === before);
  const toggle = region.getByRole('button', {name: '阅读输入正文', exact: true});
  await toggle.focus();
  await until(() => toggle.evaluate(button => button === document.activeElement), 'U093 read button did not receive focus');
  await page.keyboard.press('Enter');
  const savedBody = region.getByLabel('已收存输入正文', {exact: true}); await savedBody.waitFor();
  check('U093 scoped private body is digest verified and shown as escaped text', await savedBody.textContent() === first
    && await savedBody.locator('script').count() === 0 && !(await page.evaluate(() => window.u093Executed)));
  const closeBody = region.getByRole('button', {name: '收起输入正文', exact: true});
  check('U093 keyboard focus remains on the expanded input control', await closeBody.evaluate(button =>
    button === document.activeElement && button.getAttribute('aria-expanded') === 'true'));
  const originalWork = (await read()).works.find(w => w.id === workId), attemptId = originalWork.attempts[0].id;
  await command('recover_work', {work_id: workId, attempt_id: attemptId, reason: '受控接回原责任和原步骤'});
  await command('run_step', {work_id: workId});
  let work = (await read()).works.find(w => w.id === workId);
  check('U093 first original step adopts input once with retained source and attachment', work.inputs[0].status === 'consumed' && work.input_cursor === 1
    && work.inputs[0].source_scope.member_id === 'u093-member' && work.inputs[0].attachments.length === 1
    && work.inputs[0].attachments[0].consumed_at && work.tool_calls.length === 1);
  await page.getByRole('button', {name: '刷新工作资料依据', exact: true}).click();
  await region.getByText('已正式采用', {exact: true}).waitFor();
  await region.getByRole('button', {name: '继续补充输入', exact: true}).click();
  await body.fill(second); await region.getByLabel('补充依据', {exact: true}).fill('两原步骤之间的新要求'); await submit.click();
  await until(async () => (await read()).works.find(w => w.id === workId).inputs.length === 2, 'U093 second input not received');
  await command('run_step', {work_id: workId});
  work = (await read()).works.find(w => w.id === workId);
  const observed = await stats(), firstWire = observed.calls.at(-2).body.messages, secondWire = observed.calls.at(-1).body.messages;
  check('U093 two original steps receive inputs in order exactly once and retain original tool context', observed.inference_posts === before + 2
    && firstWire.filter(m => m.role === 'user' && m.content === first).length === 1 && !JSON.stringify(firstWire).includes(second)
    && secondWire.filter(m => m.role === 'user' && m.content === first).length === 1 && secondWire.filter(m => m.role === 'user' && m.content === second).length === 1
    && secondWire.some(m => m.role === 'tool' && JSON.parse(m.content).content === 'U093 受控原工作资料')
    && work.input_cursor === 2 && work.inputs.every(i => i.status === 'consumed') && work.attempts[0].id === attemptId && work.results.length === 1);
  await page.getByRole('button', {name: '刷新工作资料依据', exact: true}).click();
  await region.getByText('已正式采用', {exact: true}).nth(1).waitFor();
  await region.getByRole('button', {name: '继续补充输入', exact: true}).click();
  await body.fill(pending); await region.getByLabel('补充依据', {exact: true}).fill('有限预算后保留未处理要求'); await submit.click();
  await until(async () => (await read()).works.find(w => w.id === workId).inputs.length === 3, 'U093 pending input not retained');
  work = (await read()).works.find(w => w.id === workId);
  check('U093 budget exhaustion still accepts input without new Work, extra inference or false consumption', work.inputs[2].status === 'received'
    && work.input_summary.pending === 1 && work.input_cursor === 2 && work.budget.used === 2 && (await stats()).inference_posts === before + 2);
  const au = await get(page, '/api/v1/aus/' + auId);
  check('U093 adopts schema 6 for input and preserves a newer original AU schema',
    au.status === 200 && au.value.au.schema_version === Math.max(6, originalSchema));
  await page.getByRole('button', {name: '刷新工作资料依据', exact: true}).click();
  await region.getByText(/仍待采用 1 项/).waitFor();
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({width, height: 900});
    check(`U093 retained input provenance fits ${width}px`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(output, `u093-input-facts-${width}.png`), fullPage: true});
  }
  await page.goto(`${origin}/au/${auId}/work/${workId}/results/${work.results[0].id}`);
  await page.getByRole('region', {name: '成果正文', exact: true}).waitFor();
  check('U093 result displays its own input coverage while the late input stays pending',
    await page.getByText('采用至输入 2', {exact: true}).isVisible()
    && await page.getByText(`原步骤 ${work.results[0].input_step_ref} · 本步附入 ${work.inputs[1].id}`, {exact: true}).isVisible());
  page.off('request', observe);
  fs.writeFileSync(path.join(output, 'u093-inputs.json'), JSON.stringify({scope: 'controlled React/core HTTP/SQLite/modeld/SDK', real_model_calls: 0,
    extra_inference_posts: 2, original_attempt_retained: true, accepted_inputs: 3, consumed_inputs: 2, pending_inputs: 1}, null, 2) + '\n');
};
