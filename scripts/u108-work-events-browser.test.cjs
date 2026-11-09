const {test}=require('node:test');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {finishFixture}=require('./u108-work-events-browser.cjs');

for (const code of [0,7]) test('browser waits for actual fixture shutdown '+code,async()=>{
  const child=spawn(process.execPath,['-e',
    "process.stdin.once('data',()=>setTimeout(()=>process.exit(Number(process.argv[1])),50))",String(code)],
    {stdio:['pipe','pipe','inherit']});
  const completion=new Promise(resolve=>child.once('close',(code,signal)=>resolve({code,signal})));
  const closed={value:false,close(){this.value=true}};
  const result=finishFixture(child,completion,closed);
  if(code)await assert.rejects(result,/fixture shutdown failed/);else await result;
  assert.equal(child.exitCode,code);
  assert.equal(closed.value,true);
});
