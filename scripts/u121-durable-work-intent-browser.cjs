// Uses the existing loopback S02 browser, Core HTTP, SQLite and pinned modeld fixture.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

module.exports = async function durableWorkJourney({page, auId, origin, get, stats, check, until, host, hostLines,
  output, account, fixtureControl}) {
  const originWorkUrl = `/au/${encodeURIComponent(auId)}/work`;
  const read = async (tab = page) => {
    const reply = await get(tab, '/api/v1/work?' + new URLSearchParams({organization_id:auId}));
    assert.equal(reply.status, 200, reply.value.error);
    return reply.value;
  };
  const auth = (action, data = {}) => page.evaluate(async ({action, data}) => {
    const response = await fetch('/api/auth/' + action, {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)});
    return response.status;
  }, {action,data});
  const commands = [];
  const observe = request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/work/commands') commands.push(request.postDataJSON());
  };
  assert.equal((await read()).works.length, 0, 'U121 requires a real AU with no Work or existing results');
  const materialId = 'material-' + crypto.randomUUID().replaceAll('-', '');
  const materialText = 'U121 本地公开验收资料，原工作工具读取后生成结论。';
  const prep = {id:crypto.randomUUID(),organization_id:auId,base_version:(await read()).version,kind:'import_material',data:{
    material_id:materialId,name:'业务测试.md',content:materialText,source:'paste',reason:'只准在受控运行中使用本资料'}};
  const prepared = await page.evaluate(async command => {
    const response = await fetch('/api/v1/work/commands',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(command)});
    return await response.json();
  }, prep);
  assert.equal(prepared.receipt.status, 'succeeded', prepared.receipt.message);

  async function fill(tab, title, mode) {
    await tab.goto(origin + originWorkUrl);
    await tab.getByText('提出工作目标',{exact:true}).click();
    await tab.getByLabel('工作标题',{exact:true}).fill(title);
    await tab.getByLabel('目标',{exact:true}).fill('读取业务测试.md，给出原资料概要。');
    await tab.getByLabel('约束（选填）',{exact:true}).fill('只读所选资料，最多两次受控调用。');
    await tab.getByLabel('选择业务资料',{exact:true}).selectOption(`${materialId}:1`);
    await tab.getByLabel('交付方式',{exact:true}).selectOption(mode);
    return tab.getByRole('button',{name:'开始工作',exact:true});
  }
  const before = (await stats()).inference_posts;
  page.on('request',observe);
  const start = await fill(page,'U121 一次意图自动交付','automatic_text');
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({width,height:900});
    check(`U121 intent form fits ${width}px`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  }
  await fixtureControl('hold');
  let submitted, acceptedWork;
  try {
    await page.route('**/api/v1/work/commands',async route => {
      assert.equal(route.request().postDataJSON().kind,'start_work_intent');
      await route.fetch(); await route.abort('connectionreset');
    },{times:1});
    await until(() => start.isEnabled(), 'U121 authorized intent was not ready to submit');
    await start.focus();
    await until(() => start.evaluate(button => button === document.activeElement), 'U121 start button did not get focus');
    await page.keyboard.press('Enter');
    await until(async () => commands.length === 1 && (await stats()).inference_posts === before + 1,
      'U121 accepted Work did not start its first controlled model request');
    submitted = commands[0];
    const id = submitted.data.work_id;
    acceptedWork = (await read()).works.find(work => work.id === id);
    check('U121 one scoped intent creates one Work and one original attempt before releasing the model',
      submitted.kind === 'start_work_intent' && submitted.data.delivery_mode === 'automatic_text'
      && submitted.data.materials_root === materialId && submitted.data.material_version === 1
      && acceptedWork?.intent?.id === submitted.id && acceptedWork.attempts.length === 1 && acceptedWork.results.length === 0);
    await page.getByRole('button',{name:'查询开始工作的原请求',exact:true}).waitFor();
    const storage = await page.evaluate(() => JSON.stringify({session:sessionStorage, local:localStorage}));
    check('U121 response loss stores original query identity without the goal, constraint or Core password',
      storage.includes(submitted.id) && !storage.includes(submitted.data.goal) && !storage.includes(submitted.data.constraints)
      && !storage.includes(account.password));
    await page.goto(origin + '/organizations');
    assert.equal(await auth('logout'),200);
    const loggedOut = await get(page,'/api/session');
    check('U121 normal logout removes current Core read authority during original execution',
      loggedOut.status === 401 || !loggedOut.value.principal_id);
  } finally {
    await fixtureControl('release');
  }
  await until(async () => (await stats()).inference_posts === before + 2,
    'U121 background work did not run the next original model turn while logged out');
  const stillLoggedOut = await get(page,'/api/session');
  check('U121 next original turn dispatches while the browser still has no login session',
    stillLoggedOut.status === 401 || !stillLoggedOut.value.principal_id);
  assert.equal(await auth('login',{username:account.username,password:account.password,remember:false}),200);
  const workId = submitted.data.work_id;
  await until(async () => (await read()).works.find(work=>work.id===workId)?.status === 'delivered',
    'U121 exact original Work did not advance to adopted delivery');
  host.stdin.write('{"op":"restart"}\n'); assert.equal((await hostLines()).restarted,true);
  await page.goto(origin + originWorkUrl);
  await page.getByRole('button',{name:'查询开始工作的原请求',exact:true}).click();
  const rootReceipt = await get(page,'/api/v1/governance/receipts?' + new URLSearchParams({organization_id:auId,id:submitted.id}));
  const delivered = (await read()).works.find(work => work.id===workId);
  const result = delivered.results.find(item=>item.id===delivered.delivered_result_id);
  check('U121 restart preserves the original accepted receipt, one attempt, and adopted result with no browser command replay',
    rootReceipt.status === 200 && rootReceipt.value.receipt.status === 'succeeded' && rootReceipt.value.receipt.work_id === workId
    && delivered.intent.status === 'delivered' && delivered.attempts[0].id === acceptedWork.attempts[0].id
    && delivered.attempts.length === 1 && delivered.budget.used === 2 && delivered.budget.reserved === 0
    && result?.status === 'adopted' && commands.length === 1 && (await stats()).inference_posts === before + 2);
  const resultPath = originWorkUrl + `/${encodeURIComponent(workId)}/results/${encodeURIComponent(result.id)}`;
  await page.goto(origin + resultPath);
  const body = page.getByRole('region',{name:'成果正文',exact:true}); await body.waitFor();
  const [download] = await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'下载正文',exact:true}).click()]);
  check('U121 the normal U122 result route reads and downloads the actual delivered output',
    (await body.textContent()).includes(materialText) && (await fs.promises.readFile(await download.path(),'utf8')) === await body.textContent());

  const review = await page.context().newPage();
  try {
    review.on('request',observe);
    await (await fill(review,'U121 原候选治理确认','governor_review')).click();
    await until(async () => commands.length === 2 && (await read(review)).works.some(work =>
      work.id === commands[1].data.work_id && work.intent?.status === 'awaiting_decision'), 'U121 reserved decision was not recorded');
    const reviewId = commands[1].data.work_id;
    const held = (await read(review)).works.find(work => work.id === reviewId);
    const decision = held.intent.decision;
    check('U121 governor review retains one candidate with exact revision and no premature delivery',
      held.status !== 'delivered' && held.results.length === 1 && held.results[0].status === 'candidate'
      && decision.result_id === held.results[0].id && decision.sha256 === held.results[0].sha256);
    await review.goto(origin + originWorkUrl + '/' + encodeURIComponent(reviewId));
    await review.getByRole('button',{name:'批准并交付此成果',exact:true}).click();
    await until(async () => (await read(review)).works.find(work=>work.id===reviewId)?.status === 'delivered',
      'U121 explicit decision did not deliver its original result');
    const final = (await read(review)).works.find(work=>work.id===reviewId);
    check('U121 one explicit decision delivers the original candidate without further model calls or manual step commands',
      final.delivered_result_id === decision.result_id && commands.map(command=>command.kind).join(',') === 'start_work_intent,start_work_intent,decide_work_intent'
      && (await stats()).inference_posts === before + 4);
  } finally {
    review.off('request',observe); await review.close(); page.off('request',observe);
  }
  fs.writeFileSync(path.join(output,'u121-work-intent.json'),JSON.stringify({scope:'controlled real browser, Core HTTP, SQLite, modeld and pinned SDK',
    real_model_calls:0, u121_loopback_inferences:4, original_attempt_retained:true, auto_delivery_after_logout:true,
    original_receipt_recovered:true, explicit_reserved_candidate_delivery:true},null,2)+'\n');
};
