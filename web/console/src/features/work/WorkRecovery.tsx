import {useState} from 'react';
import type {CoreWorkItem,CoreWorkAttempt} from '../../api/types';
import {useWorkCommand,type WorkScope} from './useWorkCommand';

function Recovery({scope,work,attempt,version,canManage,onAccessLost}: {
  scope:WorkScope;work:CoreWorkItem;attempt:CoreWorkAttempt;version:number;canManage:boolean;onAccessLost:()=>void;
}) {
  const [editing,setEditing]=useState(false),[reason,setReason]=useState('');
  const command=useWorkCommand(scope,onAccessLost,{kind:'recover_work',workId:work.id,attemptId:attempt.id});
  const eligible=canManage&&attempt.recovery?.eligible===true;
  async function send(){
    if(!reason.trim())return;
    await command.send({work_id:work.id,attempt_id:attempt.id,reason},version,async read=>{
      const current=read.works.find(w=>w.id===work.id)?.attempts.find(a=>a.id===attempt.id);
      if(!current?.recovery?.eligible || JSON.stringify(current.execution_owner)!==JSON.stringify(attempt.execution_owner))
        throw new Error('原执行所有者或恢复资格已变化，请刷新核对');
    });
  }
  return <section aria-label="原执行恢复">
    <h3>继续原执行</h3><p>{attempt.recovery?.reason || '当前读取未报告恢复资格，请刷新核对。'}</p>
    <p>原工作、责任、模型请求和调用预约保留。未知结果只核对原请求，不重复派发。</p>
    {eligible&&!command.reference&&!editing&&<button className="button secondary" onClick={()=>setEditing(true)}>恢复原执行</button>}
    {editing&&!command.reference&&<form onSubmit={e=>{e.preventDefault();void send();}}>
      <label>恢复依据<textarea aria-label="恢复依据" value={reason} onChange={e=>setReason(e.target.value)} maxLength={10000} required/></label>
      <button className="button primary" type="submit" disabled={!eligible||!reason.trim()||command.sending||command.blocked}>确认恢复原执行</button>
      <button className="button secondary" type="button" onClick={()=>{setEditing(false);setReason('');}}>取消恢复</button>
    </form>}
    {command.reference&&<>
      <button className="button secondary" disabled={command.checking} onClick={()=>void command.lookup()}>查询恢复原请求</button>
      <details><summary>恢复请求记录</summary><p>{command.reference.id}</p></details>
      {eligible&&command.reference.resolved&&<button className="button secondary" onClick={()=>{command.another();setReason('');setEditing(true);}}>继续核对原请求</button>}
    </>}
    {command.note&&<p role="status">{command.note}</p>}
  </section>;
}
export function WorkRecovery(props:{scope:WorkScope;work:CoreWorkItem;version:number;canManage:boolean;onAccessLost:()=>void}) {
  return <>{props.work.attempts.filter(a=>a.status==='running'||a.stale).map(attempt=>
    <Recovery key={attempt.id} {...props} attempt={attempt}/>)}</>;
}
