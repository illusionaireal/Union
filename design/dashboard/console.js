"use strict";
// Offline interaction design. This API is deliberately not a production authority boundary.
(() => {
  const api = window.UNION_DESIGN_API;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const titles = {create:"创建并采用组织",start:"启动／继续有限运行",pause:"暂停新的派发",event:"提交组织事件",resources:"调整资源",amend:"修订组织章程",reconcile:"核对未知执行"};
  const defaultCharter = "只在已采用的资源与授权内进行本地试验。正式工作由有效组织决定产生。";
  let role = "board", draft = null, serial = 0;
  const time = () => new Date().toLocaleTimeString("zh-CN", {hour12:false});
  const fingerprint = s => JSON.stringify([s.orgId,s.version,s.calls,s.max,s.timeout,s.active,s.pauseRequested,s.uncertain,s.charterVersion]);
  const field = (name,label,value="",type="text",extra="") => `<label class="operation-field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra} required></label>`;
  const area = (name,label,value="") => `<label class="operation-field">${esc(label)}<textarea name="${name}" rows="3" maxlength="4000" required>${esc(value)}</textarea></label>`;
  const reason = () => area("reason","操作理由与依据");
  const button = (action,label,s,primary=false) => {const why=blocked(action,s);return `<button class="button ${primary ? "primary" : "secondary"}" data-command="${action}" ${why ? `disabled title="${esc(why)}"` : ""}>${label}</button>`;};
  function blocked(action,s){
    if(role!=="board")return "观察者可查看；操作需要发起人会话。";
    if(!s.connected)return "连接已断开，保留输入并等待新快照。";
    if(action==="start"){
      if(s.active)return "已有执行在途，不能重复启动。";
      if(s.uncertain)return "先确认原执行结果，不重新派发。";
      if(s.calls>=s.max)return "调用额度已用尽，请先调整资源。";
    }
    if(action==="pause" && (!s.active || s.pauseRequested))return s.pauseRequested ? "已请求暂停，等待在途回执。" : "当前没有派发中的运行。";
    if(["resources","amend"].includes(action) && (s.active || s.uncertain))return "先完成暂停或核对，再调整运行条件。";
    if(action==="amend" && s.boardCanAmend===false)return "旧章程未授予修订权限。";
    if(action==="reconcile" && s.uncertain!=="unknown")return "仅可核对已确认结果未知的执行。";
    return "";
  }
  function controls(){
    const s=api.read();
    $("role-label").textContent=role==="board" ? "模拟发起人" : "模拟观察者";
    $("console-controls").innerHTML=`<div class="console-buttons">${button("create","＋ 新建组织",s)}${button("start","启动／继续",s,true)}${button("pause","暂停派发",s)}${button("event","提交事件",s)}${s.uncertain ? button("reconcile","核对执行",s) : ""}<button class="text-button" data-action="navigate" data-key="settings">组织设置 →</button></div><p class="console-hint">${esc(role!=="board" ? "观察者视角：仅查看，模拟写操作已禁用。" : !s.connected ? "连接断开：旧快照可查看，操作暂不可提交。" : s.pauseRequested ? "暂停已请求：不再派发下一步，仍需等待在途回执。" : s.uncertain ? "原执行结果尚未确认；核对之前保持调用占用。" : "所有操作仅影响当前页面的模拟数据；刷新文档会重置。")}</p>`;
    $("complete-simulation").disabled=!s.active || !s.connected;
    window.UNION_CONSOLE_STATE={role,orgId:s.orgId,active:s.active,pauseRequested:!!s.pauseRequested,calls:s.calls,max:s.max,receipts:s.receipts,uncertain:s.uncertain,real_model_calls:0};
  }
  window.UNION_CONSOLE_SETTINGS = s => `<div class="cards-grid"><section class="card console-card"><div class="eyebrow">RESOURCES</div><h2>有限资源</h2><dl class="detail-dl"><div><dt>总调用上限</dt><dd>${s.max} 次</dd></div><div><dt>累计占用</dt><dd>${s.calls} 次</dd></div><div><dt>单次超时</dt><dd>${s.timeout} 秒</dd></div><div><dt>金额费用</dt><dd>未知</dd></div></dl>${button("resources","调整资源",s)}<p>调整保留已有调用；原型不产生任何真实费用。</p></section><section class="card console-card"><div class="eyebrow">CHARTER · V${s.charterVersion}</div><h2>已采用章程</h2><p class="charter-copy">${esc(s.charter || defaultCharter)}</p><p>本地工具：${s.toolsAllowed===false ? "无" : "文本成果"} · 旧规则允许修章：${s.boardCanAmend===false ? "否" : "是"}</p>${button("amend","预览修章",s)}${s.uncertain ? button("reconcile","核对未知执行",s) : ""}</section></div><section class="card console-card receipt-card"><h2>操作回执 <span class="badge purple">设计模拟</span></h2><p>当前组织 ${esc(s.orgId)} · 浏览器内的临时记录</p><div id="receipt-list">${s.receipts.length ? [...s.receipts].reverse().map(r=>`<article class="command-receipt"><div><strong>${esc(r.title)}</strong><span class="badge ${r.status==="已拒绝" ? "red" : r.status==="已受理" ? "amber" : "green"}">${esc(r.status)}</span></div><p>${esc(r.message)}</p><small>${esc(r.id)} · ${esc(r.actor)} · ${esc(r.time)} · 基准 v${r.base} · ${esc(r.orgId)}</small></article>`).join("") : '<div class="empty-state"><strong>还没有操作回执</strong><p>先预览并提交一项模拟操作。</p></div>'}</div></section>`;
  function forms(action,s){
    if(action==="create")return field("name","组织名称","我的试验组织","text",'maxlength="80"')+area("goal","组织目标","在有限资源内完成一次有证据的协作。")+field("adopter","采用人","模拟发起人","text",'maxlength="80"')+area("charter","采用的章程正文",defaultCharter)+`<p class="form-note">规则采用本地测试模板：现有组织操作、文本成果工具、董事会修章入口；不包含发布或支付权限。</p>`+field("max","累计调用上限",8,"number",'min="1" max="100" step="1"')+field("timeout","单次超时（秒）",180,"number",'min="1" max="3600" step="1"');
    if(action==="start")return `<p class="form-note">已占用 ${s.calls} / ${s.max} 次；剩余 ${s.max-s.calls} 次，单次超时 ${s.timeout} 秒。真实模型调用始终为 0。</p><label class="operation-field">执行器情景<select name="executor"><option value="fixture">Fixture · 确定性模拟</option><option value="codex">Codex · 仅演示费用确认流程</option></select></label>`+field("steps","本次最多执行步数",1,"number",`min="1" max="${s.max-s.calls}" step="1"`)+`<label class="check-field"><input type="checkbox" name="acceptCost">演示接受有限调用的费用未知条件（本原型不调用 Codex）</label>`;
    if(action==="pause")return `<p class="form-note">当前有在途模拟执行。提交后停止后续派发；收到回执后才能确认已暂停。这不表示远程调用已取消。</p>`;
    if(action==="event")return `<label class="operation-field">事件类型<select name="kind"><option value="opinion">发起人意见</option><option value="external_feedback">外部反馈</option></select></label>`+area("content","事件内容")+field("source","来源","用户在原型中的输入","text",'maxlength="200"')+`<label class="operation-field">输入来源标记<select name="simulated"><option value="true">模拟资料</option><option value="false">真实来源声明（原型仍不构成验证）</option></select></label><p class="form-note">来源声明需要另行核验。意见进入事件列表，是否采纳由有效组织决定形成。</p>`;
    if(action==="resources")return `<p class="form-note">当前 ${s.max} 次上限、${s.timeout} 秒超时；已有 ${s.calls} 次占用不会返还。</p>`+field("max","新的累计调用上限",s.max,"number",`min="${Math.max(1,s.calls)}" max="100" step="1"`)+field("timeout","新的单次超时（秒）",s.timeout,"number",'min="1" max="3600" step="1"')+reason();
    if(action==="amend")return area("charter","新章程正文",s.charter || defaultCharter)+`<label class="operation-field">允许的本地工具<select name="tools"><option value="text" ${s.toolsAllowed!==false ? "selected" : ""}>文本成果工具</option><option value="none" ${s.toolsAllowed===false ? "selected" : ""}>撤回文本成果工具</option></select></label><p class="form-note">组织操作、保留事项与修章入口沿用当前采用的模板。本设计表单仅演示正文与工具字段修订；正文不会隐式授予权限。撤回工具后相关未完成工作不能继续派发。</p>`+reason();
    return `<p class="form-note">目标执行：design-run-${s.calls}，已确认结果未知。没有自动导入远程成果的功能。</p><label class="operation-field">核对结论<select name="resolution"><option value="confirmed_not_executed">有依据确认未执行</option><option value="abandon">放弃本次执行</option></select></label>`+reason();
  }
  function showError(message){$("operation-error").textContent=message;$("operation-error").hidden=false;}
  function open(action){
    const s=api.read(),why=blocked(action,s);if(why){api.notify(why);return;}
    draft={action,submitted:false};
    $("operation-title").textContent=titles[action];$("operation-fields").innerHTML=forms(action,s);
    $("operation-form").hidden=false;$("operation-result").hidden=true;$("operation-error").hidden=true;
    $("operation-preview").hidden=true;$("commit-operation").hidden=true;
    $("operation-dialog").showModal();
  }
  function validate(action,data,s){
    const why=blocked(action,s);if(why)return why;
    if(["create","resources"].includes(action) && (!Number.isInteger(+data.max) || +data.max<Math.max(1,action==="create" ? 0 : s.calls) || +data.max>100 || !Number.isInteger(+data.timeout) || +data.timeout<1 || +data.timeout>3600))return "请输入有效的有限调用与超时条件。";
    if(action==="start" && (!Number.isInteger(+data.steps) || +data.steps<1 || +data.steps>s.max-s.calls))return "本次步数必须是剩余调用范围内的正整数。";
    if(action==="start" && data.executor==="codex" && !data.acceptCost)return "请明确选择接受费用未知条件，再预览；原型仍不调用模型。";
    if(action==="start" && s.toolsAllowed===false)return "当前模拟章程撤回了文本成果工具，先在有效规则内处理权限。";
    if(Object.values(data).some(v=>typeof v==="string" && !v.trim()))return "必填内容不能只包含空格。";
    return "";
  }
  function preview(event){
    event.preventDefault();if(!draft || draft.submitted)return;
    const s=api.read(),data=Object.fromEntries(new FormData($("operation-form")));
    const error=validate(draft.action,data,s);if(error){showError(error);return;}
    draft.data=data;draft.fingerprint=fingerprint(s);draft.base=s.version;draft.orgId=s.orgId;draft.id=`design-command-${++serial}`;
    const impacts={create:`创建「${data.name}」并采用目标与章程；上限 ${data.max} 次，超时 ${data.timeout} 秒；不自动运行。`,start:`受理最多 ${data.steps} 步的模拟运行，每次派发占用一次；回执由操作情景工具模拟到达。选择 ${data.executor} 不会启动实际模型。`,pause:"先登记暂停请求，保持当前调用占用与在途状态。",event:`记录 ${data.kind}；来源：${data.source}；输入声明为${data.simulated==="true" ? "模拟" : "真实"}。不直接生成任务。`,resources:`总调用上限 ${s.max} → ${data.max}；单次超时 ${s.timeout} → ${data.timeout} 秒；保留 ${s.calls} 次占用。`,amend:`章程 v${s.charterVersion} → v${s.charterVersion+1}；工具 ${s.toolsAllowed===false ? "无" : "文本成果"} → ${data.tools==="none" ? "无" : "文本成果"}；撤权会阻止相关后续派发。`,reconcile:`处理 design-run-${s.calls}：${data.resolution==="abandon" ? "放弃执行" : "确认未执行，允许后续重新安排"}；不退款、不自动重试。`};
    $("operation-preview").innerHTML=`<h3>确认影响</h3><p>${esc(impacts[draft.action])}</p>${draft.action==="amend" ? `<div class="charter-diff"><strong>旧正文</strong><p>${esc(s.charter || defaultCharter)}</p><strong>新正文</strong><p>${esc(data.charter)}</p></div>` : ""}<small>目标：${esc(s.name)} · ${esc(s.orgId)} · 基准 v${s.version}<br>请求 ${draft.id} · 模拟发起人</small>`;
    $("operation-preview").hidden=false;$("commit-operation").hidden=false;$("operation-error").hidden=true;$("commit-operation").focus();
  }
  function log(s,title,description){s.extraEvents.push({id:`console-event-${++serial}`,type:"event",title,description:`${description}（设计模拟）`,time:time(),task:null});}
  function stage(s){
    if(!s.memberCount)return 0;
    if(s.tasks[0]==="pending")return 1;
    if(s.tasks[0]==="delivered" && ["dependent","pending"].includes(s.tasks[1]))return 2;
    if(s.artifacts===2 && s.tasks.length===2)return 3;
    if(s.tasks[2]==="pending")return 4;
    return 5;
  }
  const runNames=["形成组织安排","生成模拟资料","使用依赖成果","依据成果形成决定","执行后续工作","登记持久等待"];
  function dispatch(s){
    const step=stage(s);s.calls++;s.active=true;s.activeStep=step;s.pauseRequested=false;s.paused=false;
    s.runOverrides={...s.runOverrides,[s.calls]:"running"};s.runNames={...s.runNames,[s.calls]:runNames[step]};
    const task={1:0,2:1,4:2}[step];
    s.runTasks={...s.runTasks,[s.calls]:task===undefined ? null : ["work-one","work-two","work-followup"][task]};
    if(task!==undefined){s.tasks[task]="running";s.taskRunIds={...s.taskRunIds,[task]:"design-run-"+s.calls};s.version++;}
    s.title="运行请求已受理";s.tone="purple";s.now=`正在演示：${runNames[step]}，尚未收到结果。`;s.next="通过操作情景工具模拟收到回执，或请求暂停后续派发。";s.live="原型活性：有效（设计模拟）";
  }
  function commit(){
    if(!draft || !draft.data || draft.submitted)return;
    let s=api.read();
    const invalid=validate(draft.action,draft.data,s) || (draft.fingerprint!==fingerprint(s) ? "状态或资源已变化。输入已保留，请重新预览。" : "");
    if(invalid){showError(invalid);$("commit-operation").hidden=true;return;}
    draft.submitted=true;
    const d=draft.data,a=draft.action;
    if(a==="create")s={...api.initial("empty"),name:d.name,goal:d.goal,charter:d.charter,adopter:d.adopter,orgId:`org-design-${serial}`,max:+d.max,timeout:+d.timeout};
    if(a==="start"){s.runRemaining=+d.steps;s.runRequest=draft.id;dispatch(s);}
    if(a==="pause"){s.pauseRequested=true;s.pauseRequest=draft.id;s.title="暂停已请求";s.tone="amber";s.next="等待当前在途回执后暂停；不派发下一步。";}
    if(a==="event")log(s,"已提交："+d.content,`来源 ${d.source}；输入声明 ${d.simulated==="true" ? "模拟" : "真实（未核验）"}；类型 ${d.kind}`);
    if(a==="resources"){s.max=+d.max;s.timeout=+d.timeout;s.version++;if(s.title==="额度已用尽" && s.calls<s.max){s.title="可以继续运行";s.next="重新预览有限运行条件。";}}
    if(a==="amend"){s.charter=d.charter;s.toolsAllowed=d.tools!=="none";s.charterVersion++;s.version++;s.next=s.toolsAllowed ? "新行动按已修订规则校验。" : "文本成果工具已撤回，相关工作不能继续派发。";}
    if(a==="reconcile"){
      s.uncertain=null;s.version++;s.runOverrides={...s.runOverrides,[s.calls]:d.resolution==="abandon" ? "cancelled" : "failed"};
      s.tasks=s.tasks.map(status=>status==="needs_review" ? d.resolution==="abandon" ? "cancelled" : "pending" : status);
      s.title="核对已记录";s.tone="amber";s.now="原执行已经人工核对；调用占用保留。";s.next="如需继续，请另行预览有限运行。";s.live="原型活性：无执行进程";
    }
    const receipt={id:draft.id,title:titles[a],orgId:s.orgId,actor:"模拟发起人",time:time(),base:draft.base,status:["start","pause"].includes(a) ? "已受理" : "已完成",message:a==="start" ? "已受理模拟运行，等待执行回执。" : a==="pause" ? "已登记暂停意图，等待在途结束。" : "模拟操作已记录；真实服务未接入。",reason:d.reason || ""};
    s.receipts.push(receipt);if(a!=="event")log(s,titles[a],d.reason || receipt.message);
    api.update(s);
    $("operation-form").hidden=true;$("operation-result").hidden=false;
    $("operation-result").innerHTML=`<div class="operation-success"><span class="badge ${receipt.status==="已受理" ? "amber" : "green"}">${receipt.status} · 模拟</span><h3>${esc(receipt.message)}</h3><p>${esc(receipt.id)} · ${esc(s.name)}</p><p>真实模型调用 0 · 页面内临时数据</p></div><button type="button" class="button primary" id="show-receipts">查看操作回执 →</button>`;
    $("show-receipts").focus();
  }
  function complete(){
    const s=api.read();if(!s.active || !s.connected)return;
    const step=s.activeStep,paused=s.pauseRequested;
    s.active=false;s.pauseRequested=false;s.runOverrides={...s.runOverrides,[s.calls]:"delivered"};s.version++;
    if(step===0){s.memberCount=2;s.tasks=["pending","dependent"];s.activity=1;}
    if(step===1){s.tasks[0]="delivered";s.tasks[1]="pending";s.artifacts=1;}
    if(step===2){s.tasks[1]="delivered";s.artifacts=2;}
    if(step===3)s.tasks.push("pending");
    if(step===4){s.tasks[2]="delivered";s.artifacts=3;}
    s.runRemaining=Math.max(0,(s.runRemaining || 1)-1);
    log(s,"模拟收到执行回执",runNames[step]);
    if(!paused && step!==5 && s.runRemaining>0 && s.calls<s.max)dispatch(s);
    else{
      s.paused=paused;s.title=paused ? "已暂停派发" : step===5 ? "等待新事件" : s.calls>=s.max ? "额度已用尽" : "本次有限运行已结束";
      s.tone="amber";s.now="当前在途模拟执行已结束，调用占用保留。";s.next=paused ? "可以调整资源或章程，再明确继续运行。" : "查看成果与回执，按资源条件决定是否继续。";s.live="原型活性：无执行进程";
      for(const receipt of s.receipts)if([s.runRequest,s.pauseRequest].includes(receipt.id)){receipt.status="已完成";receipt.message=paused ? "已收到在途回执，暂停已生效。" : "有限模拟运行已结束。";}
      s.runRemaining=0;
    }
    api.update(s);api.notify(s.active ? "模拟回执已接收，有限步数内进入下一步。" : "模拟回执已接收，当前没有在途执行。");
  }
  document.addEventListener("union-design-render",controls);
  document.addEventListener("click",event=>{
    const command=event.target.closest("[data-command]");if(command && !command.disabled)open(command.dataset.command);
    if(event.target.id==="show-receipts"){$("operation-dialog").close();api.navigate("settings");}
  });
  $("operation-form").addEventListener("submit",preview);
  $("operation-form").addEventListener("input",()=>{if(draft){delete draft.data;$("operation-preview").hidden=true;$("commit-operation").hidden=true;}});
  $("commit-operation").addEventListener("click",commit);
  for(const id of ["close-operation","cancel-operation"])$(id).addEventListener("click",()=>$("operation-dialog").close());
  $("operation-dialog").addEventListener("close",()=>{draft=null;});
  $("console-role").addEventListener("change",()=>{role=$("console-role").value;api.render();});
  $("complete-simulation").addEventListener("click",complete);
  api.render();
})();
