// Actual original-Work recovery UI, HTTP, SQLite and controlled modeld/SDK.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
module.exports = async function recoveryJourney({page,auId,origin,get,stats,check,until,host,hostLines,output}) {
  const read = async () => (await get(page,'/api/v1/work?organization_id='+auId)).value;
  const command = async (kind,data) => {
    const value=await read();
    const response=await page.evaluate(async body=>{const r=await fetch('/api/v1/work/commands',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});return {status:r.status,value:await r.json()};},
      {id:crypto.randomUUID(),organization_id:auId,base_version:value.version,kind,data});
    assert.equal(response.status,200,response.value.error);assert.equal(response.value.receipt.status,'succeeded',response.value.receipt.message);
    return response.value.receipt;
  };
  const models=(await get(page,'/api/v1/models?organization_id='+auId)).value;
  const connection=models.connections.find(c=>c.is_default);
  const materialId='material-'+crypto.randomUUID().replaceAll('-',''),workId='u092-original-work';
  await command('import_material',{material_id:materialId,name:'业务测试.md',content:'原执行的公开资料恢复标识',source:'paste',reason:'受控恢复验收只读资料'});
  await command('start_work',{work_id:workId,title:'U092 原工作恢复',goal:'读取业务测试.md 并给出结论',member_name:'受控成员',member_id:'u092-member',binding_id:'u092-binding',mandate_id:'u092-mandate',definition_id:'u092-definition',connection_id:connection.id,expected_revision:connection.revision,materials_root:materialId,material_version:1,max_calls:2,tools:['read_document'],reason:'受控恢复验收，不调用真实模型'});
  await command('start_attempt',{work_id:workId});
  const before=(await stats()).inference_posts;
  await command('run_step',{work_id:workId});
  const original=(await read()).works.find(w=>w.id===workId),attemptId=original.attempts[0].id;
  check('U092 actual original tool/context commit exists before restart',original.tool_calls.length===1&&original.results.length===0&&(await stats()).inference_posts===before+1);
  host.stdin.write('{"op":"restart"}\n');assert.equal((await hostLines()).restarted,true);
  await page.goto(`${origin}/au/${auId}/work/${workId}`);
  const region=page.getByRole('region',{name:'原执行恢复',exact:true});
  await region.getByRole('button',{name:'恢复原执行',exact:true}).waitFor();
  for(const width of [1440,1024,768,390,320]) {
    await page.setViewportSize({width,height:900});
    check(`U092 original recovery fits ${width}px`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,`u092-recovery-${width}.png`),fullPage:true});
  }
  await region.getByRole('button',{name:'恢复原执行',exact:true}).focus();await page.keyboard.press('Enter');
  await region.getByLabel('恢复依据',{exact:true}).fill('接回原资料读取和责任，不重派原模型');
  let recovery;
  const observe=request=>{if(request.method()==='POST'&&new URL(request.url()).pathname==='/api/v1/work/commands'&&request.postDataJSON().kind==='recover_work')recovery=request.postDataJSON();};
  page.on('request',observe);
  await page.route('**/api/v1/work/commands',async route=>{await route.fetch();await route.abort('connectionreset');},{times:1});
  await region.getByRole('button',{name:'确认恢复原执行',exact:true}).click();
  await region.getByRole('button',{name:'查询恢复原请求',exact:true}).waitFor();
  await until(async()=>!!recovery,'Recovery POST not observed');
  check('U092 UI submits only original Work/attempt/reason through one scoped command',recovery.data.work_id===workId&&recovery.data.attempt_id===attemptId&&Object.keys(recovery.data).length===3);
  const privateCache=await page.evaluate(()=>JSON.stringify(sessionStorage));
  check('U092 recovery persists original request metadata without reason or model body',privateCache.includes(recovery.id)&&!privateCache.includes('接回原资料读取和责任'));
  host.stdin.write('{"op":"restart"}\n');assert.equal((await hostLines()).restarted,true);
  await page.reload();await region.getByRole('button',{name:'查询恢复原请求',exact:true}).click();
  await region.getByRole('status').waitFor();
  const receipt=await get(page,'/api/v1/governance/receipts?'+new URLSearchParams({organization_id:auId,id:recovery.id}));
  check('U092 lost response and second restart query original receipt without model replay',receipt.status===200&&receipt.value.receipt.status==='succeeded'&&(await stats()).inference_posts===before+1);
  // A fresh explicit recovery takes ownership after the second restart; no new attempt.
  await region.getByRole('button',{name:'继续核对原请求',exact:true}).click();
  await region.getByLabel('恢复依据',{exact:true}).fill('再次接回同一执行');
  await region.getByRole('button',{name:'确认恢复原执行',exact:true}).click();
  await until(async()=>{const w=(await read()).works.find(w=>w.id===workId);return !w.attempts[0].stale;},'New host did not take original ownership');
  await command('run_step',{work_id:workId});
  const completed=(await read()).works.find(w=>w.id===workId);
  check('U092 same attempt resumes original tool context into actual result',completed.attempts.length===1&&completed.attempts[0].id===attemptId&&completed.results.length===1&&completed.budget.reserved===0&&completed.budget.used===2&&(await stats()).inference_posts===before+2);
  const supplied=(await stats()).calls.at(-1).body.messages.find(m=>m.role==='tool');
  check('U092 recovered next step retains original tool pairing and body',supplied&&JSON.parse(supplied.content).content==='原执行的公开资料恢复标识');
  page.off('request',observe);
  fs.writeFileSync(path.join(output,'u092-recovery.json'),JSON.stringify({scope:'controlled React/HTTP/SQLite/modeld/SDK',real_model_calls:0,extra_inference_posts:2},null,2)+'\n');
};
