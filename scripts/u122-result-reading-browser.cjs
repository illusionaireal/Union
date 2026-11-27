// U122 consumes the existing isolated core/S02/modeld browser fixture. It adds no inference.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

module.exports = async function resultReading({page, auId, origin, get, stats, check, until, output}) {
  const before = (await stats()).inference_posts;
  const read = async () => (await get(page, '/api/v1/work?' + new URLSearchParams({organization_id:auId}))).value;
  const command = async (kind, data) => {
    const current = await read();
    const response = await page.evaluate(async payload => {
      const r = await fetch('/api/v1/work/commands', {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});
      return {status:r.status,value:await r.json()};
    }, {id:crypto.randomUUID(),organization_id:auId,base_version:current.version,kind,data});
    assert.equal(response.status,200,response.value.error || kind); assert.equal(response.value.receipt.status,'succeeded',response.value.receipt.message);
    return response.value.receipt;
  };
  const first = (await read()).works.find(w => w.id === 'u120-original-work' && w.results.length);
  assert(first, 'Controlled model fixture must have a real persisted candidate result');
  const result = first.results[0];
  const original = await get(page, '/api/v1/work/results?' + new URLSearchParams({organization_id:auId,work_id:first.id,id:result.id}));
  assert.equal(original.status,200);
  // Explicit controlled preparation only; this does not claim U121 autonomous creation.
  const secondId = 'u122-second-work';
  const materialId = 'material-' + crypto.randomUUID().replaceAll('-','');
  await command('import_material',{material_id:materialId,name:'U122公开测试资料.md',content:'仅供受控成果阅读验收的公开测试资料',source:'paste',reason:'明确授权受控fixture资料只读，不派发模型'});
  const models = (await get(page, '/api/v1/models?' + new URLSearchParams({organization_id:auId}))).value;
  const connection = models.connections.find(c => c.id === first.definition.connection_id);
  await command('start_work',{work_id:secondId,title:'U122 同名成果隔离工作',goal:'保存公开受控测试成果供正文阅读验收',
    member_name:'受控研究成员',member_id:'u122-member',binding_id:'u122-binding',mandate_id:'u122-mandate',definition_id:'u122-definition',
    connection_id:connection.id,expected_revision:connection.revision,materials_root:materialId,material_version:1,max_calls:1,tools:['read_document'],reason:'仅受控阅读fixture，不派发模型'});
  await command('start_attempt',{work_id:secondId});
  const body = '乙工作自己的公开成果\n<script>window.resultExecuted=true</script>\n长行：' + '研究依据与结论。'.repeat(100);
  await command('submit_result',{work_id:secondId,result_id:result.id,title:'U122 第二份同名标识成果',content:body,sources:[]});
  const second = (await read()).works.find(w => w.id === secondId);
  const ambiguous = await get(page, '/api/v1/work/results?' + new URLSearchParams({organization_id:auId,id:result.id}));
  check('U122 ambiguous result ID without Work is rejected by actual core HTTP',ambiguous.status===400 && !('content' in ambiguous.value));
  const noSuchWork = await get(page, '/api/v1/work/results?' + new URLSearchParams({organization_id:auId,work_id:'u122-missing',id:result.id}));
  check('U122 missing Work never falls back to a matching result in another Work',noSuchWork.status===400 && !('content' in noSuchWork.value));
  await page.goto(`${origin}/au/${auId}/results`);
  const links = page.getByRole('link',{name:'阅读与下载',exact:true});await links.first().waitFor();
  const hrefs = await links.evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
  check('U122 actual list keeps both equal result IDs in separate Work routes',hrefs.includes(`/au/${auId}/work/${first.id}/results/${result.id}`)
    && hrefs.includes(`/au/${auId}/work/${secondId}/results/${result.id}`));
  await page.goto(`${origin}/au/${auId}/work/${secondId}/results/${result.id}`);
  const text = page.getByRole('region',{name:'成果正文',exact:true});await text.waitFor();
  check('U122 displays the second Work body with its own UTF8 digest',await text.textContent()===body
    && (await page.getByText(/UTF-8/).last().textContent()).includes(crypto.createHash('sha256').update(body).digest('hex')));
  check('U122 externally supplied HTML remains literal text',await text.locator('script').count()===0 && await page.evaluate(()=>window.resultExecuted)!==true);
  const downloading = page.waitForEvent('download');
  await page.getByRole('button',{name:'下载正文',exact:true}).click();const downloaded=await downloading;
  check('U122 downloads plain same-Work body rather than JSON',downloaded.suggestedFilename()===`${secondId}-${result.id}-v1.txt`
    && fs.readFileSync(await downloaded.path(),'utf8')===body);
  await page.reload();await text.waitFor();check('U122 direct refresh retains original Work/result version',await text.textContent()===body);
  for(const width of [1440,1024,768,390,320]) {
    await page.setViewportSize({width,height:900});
    check(`U122 result body and provenance fit ${width}px`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,`u122-results-${width}.png`),fullPage:true});
  }
  await page.getByRole('button',{name:'下载正文',exact:true}).focus();await page.keyboard.press('Tab');
  check('U122 keyboard moves from download to explicit refresh',await page.getByRole('button',{name:'刷新成果',exact:true}).evaluate(n=>n===document.activeElement));
  await page.getByRole('link',{name:'返回原工作',exact:true}).click();await page.getByRole('heading',{name:'U122 同名成果隔离工作',exact:true}).waitFor();
  check('U122 returns to the original Work route',new URL(page.url()).pathname===`/au/${auId}/work/${secondId}`);
  await command('finish_attempt',{work_id:secondId,attempt_id:second.attempts.find(a=>a.status==='running').id,outcome:'stopped',reason:'受控阅读fixture准备完成'});
  await command('adopt_result',{work_id:secondId,result_id:result.id});await command('deliver_work',{work_id:secondId,result_id:result.id});
  await page.goto(`${origin}/au/${auId}/work/${secondId}/results/${result.id}`);await text.waitFor();
  check('U122 actual adopted and delivered facts are separate from candidate state',await page.getByText('已采用',{exact:true}).isVisible()
    && await page.getByText('已交付',{exact:true}).isVisible() && await page.getByText(/采用主体与时间/).isVisible());
  await page.goto(`${origin}/au/${auId}/work/${first.id}/results/${result.id}`);await text.waitFor();
  check('U122 the first Work still opens its original controlled model output',await text.textContent()===original.value.content);
  const preparedModels=(await get(page,'/api/v1/models?'+new URLSearchParams({organization_id:auId}))).value;
  const preparedMaterials=(await get(page,'/api/v1/work/materials?'+new URLSearchParams({organization_id:auId}))).value;
  const preparedWork=await read();
  check('U112 complete preparation retains legal default model, finite grant and separately authorized business material',
    preparedModels.connections.some(c=>c.enabled&&c.is_default) && preparedModels.resources.grant!==null
    && preparedModels.document_read_allowed===true && preparedMaterials.materials.some(m=>m.id===materialId&&m.read_allowed)
    && preparedWork.access.can_start===true);
  check('U112 business material preparation stays separate from S02 validation attachments and activation',
    second.materials_root===materialId && preparedWork.capabilities.autonomous_business===false);
  fs.writeFileSync(path.join(output,'u112-preparation.json'),JSON.stringify({scope:'controlled complete preparation journey',
    normal_page_model_and_material_preparation:true,original_work_read_provenance:result.sources,real_model_calls:0,
    autonomous_business:false,observed_at:new Date().toISOString()},null,2));
  let release, captured;
  const late=new Promise(resolve=>{release=resolve;});const reached=new Promise(resolve=>{captured=resolve;});
  await page.route('**/api/v1/work/results?*',async route=>{const response=await route.fetch();captured();await late;await route.fulfill({response}).catch(()=>{});},{times:1});
  await page.getByRole('button',{name:'刷新成果',exact:true}).click();await reached;
  await page.getByRole('link',{name:'我的组织',exact:true}).click();release();
  await page.getByRole('heading',{name:'我的组织',exact:true}).waitFor();
  check('U122 leaving AU clears body and ignores the late original read',await page.getByRole('region',{name:'成果正文',exact:true}).count()===0);
  check('U122 all result reading checks dispatch no additional inference',(await stats()).inference_posts===before);
  fs.writeFileSync(path.join(output,'u122-result-reading.json'),JSON.stringify({scope:'controlled real browser/core HTTP/SQLite',real_model_calls:0,
    new_inference_posts:0,first_work:first.id,second_work:secondId,result_id:result.id,observed_at:new Date().toISOString()},null,2));
};
