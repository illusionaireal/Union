"use strict";
(() => {
  const publicData = window.UNION_PROTOTYPE_DATA;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const icons = {
    overview: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    members: '<circle cx="9" cy="7" r="3"/><path d="M3 20v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 5"/>',
    tasks: '<rect x="5" y="4" width="15" height="17" rx="2"/><path d="M9 2h7v4H9zM9 11h7M9 16h7"/>',
    artifacts: '<path d="M6 3h8l5 5v13H6zM14 3v5h5M10 13h5M10 17h5"/>',
    activity: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    resources: '<path d="M4 20h17M7 16V9M12 16V4M17 16v-5"/>',
    settings: '<path d="M4 7h16M4 17h16M8 4v6M16 14v6"/>',
  };
  const pages = {
    overview: ["总览", "组织总览", "从当前行动，到下一轮决定。"],
    members: ["成员与岗位", "成员与岗位", "稳定身份、明确责任，以及可以延续的协作。"],
    tasks: ["工作", "工作与依赖", "每一项工作都有责任人、依据和可追溯的结果。"],
    artifacts: ["成果", "组织成果", "打开实际内容，核对来源与版本。此处为公开模拟成果。"],
    activity: ["活动", "事件与决定", "当前状态如何形成，后续行动因何发生。"],
    resources: ["执行与资源", "执行与资源", "调用有边界，回执有来源，未知费用如实显示。"],
    settings: ["组织设置", "组织设置与回执", "采用规则、调整资源，并确认每次操作的结果。"],
  };
  const statuses = {
    delivered: ["已交付", "green"], running: ["执行中 · 模拟", "purple"], pending: ["待执行", "grey"],
    dependent: ["等待依赖", "amber"], needs_review: ["待核对", "red"], unconfirmed: ["活性未确认", "amber"],
    waiting: ["等待新事件", "amber"], failed: ["失败", "red"], rejected: ["决定被拒绝", "red"],
    cancelled: ["已放弃", "grey"],
  };
  const members = [
    {id:"fixture-one", name:"测试成员 A", short:"A", role:"测试责任一", assignment:"assignment-one", tone:"", description:"形成前置资料，并承担测试场景中的组织决定责任。岗位由运行决定形成。"},
    {id:"fixture-two", name:"测试成员 B", short:"B", role:"测试责任二", assignment:"assignment-two", tone:"mint", description:"使用成员 A 的依赖资料，交付成果，并执行根据成果形成的后续工作。"},
  ];
  const taskDefinitions = publicData.work.map((task, index) => ({...task, index, instruction: ["生成用于跨成员协作的模拟资料，并保存为可校验的文本成果。", "读取 source.md 的具体内容，在工作结果中体现前置资料的使用。", "依据前两项已交付工作执行后续动作，保存可以读取的成果。 "][index]}));
  let pageKey = "overview", scenario = "working", state, sequence = 0, eventFilter = "all", visibleEvents = 5;
  let query = "", taskFilter = "all", memberFilter = "all", toastTimer, acceptedTime = "";
  const initial = key => {
    const configs = {
      working: {version:4,calls:3,max:8,tasks:["delivered","running"],artifacts:1,title:"协作进行中",tone:"purple",now:"成员 B 正在使用成员 A 的资料，完成依赖工作。",next:"接收 dependent.md，提交交付事件与下一轮决定。",activity:3,live:"原型活性：有效（设计模拟）"},
      waiting: {version:9,calls:6,max:8,tasks:["delivered","delivered","delivered"],artifacts:3,title:"等待新事件",tone:"amber",now:"三项模拟工作已交付，组织保存状态并等待新的依据。",next:"等待新事件。测试复查时间为 2099 年，不代表实际经营安排。",activity:7,live:"原型活性：无执行进程"},
      unknown: {version:5,calls:3,max:8,tasks:["delivered","needs_review"],artifacts:1,title:"执行待核对",tone:"red",now:"成员 B 的执行结果未知，原任务保留并等待核对。",next:"在受信入口核对原执行结果，确认前不重新派发。",activity:3,live:"原型活性：已确认中断"},
      unconfirmed: {version:4,calls:3,max:8,tasks:["delivered","unconfirmed"],artifacts:1,title:"活性未确认",tone:"amber",now:"存在 running 记录，但没有足够依据确认执行进程仍活跃。",next:"先确认执行活性与结果；此时不能据记录宣布正常执行或重派。",activity:3,live:"原型活性：未确认"},
      budget: {version:1,calls:1,max:1,tasks:["pending","dependent"],artifacts:0,title:"额度已用尽",tone:"amber",now:"启动已占用唯一调用额度，工作尚未执行。",next:"在组织设置中预览资源调整；已占用调用保持不变。",activity:1,live:"原型活性：无执行进程"},
      empty: {version:0,calls:0,max:8,tasks:[],artifacts:0,title:"组织尚未形成",tone:"grey",now:"目标和测试章程已准备，尚未形成成员与工作。",next:"预览有限运行条件，明确启动后等待有效组织决定。",activity:0,live:"原型活性：无执行进程"},
      rejected: {version:6,calls:4,max:8,tasks:["delivered","delivered"],artifacts:2,title:"决定被拒绝",tone:"red",now:"后续决定的依据版本冲突，正式工作没有因此改变。",next:"保留拒绝依据；在有效状态和资源内形成新决定。",activity:4,live:"原型活性：无执行进程"},
      unavailable: {version:9,calls:6,max:8,tasks:["delivered","delivered","delivered"],artifacts:3,title:"成果文件待核验",tone:"red",now:"source.md 的文件校验失败，历史交付记录仍保留。",next:"核对原文件与来源；不可用内容不展示、不下载。",activity:7,live:"原型活性：无执行进程",unavailable:"source.md"},
    };
    return {...configs[key], tasks:[...configs[key].tasks], connected:true, extraEvents:[], name:"测试组织", orgId:"org-design-fixture", charterVersion:1, timeout:180, receipts:[], memberCount:key==="empty" ? 0 : 2, active:key==="working", uncertain:key==="unknown" ? "unknown" : key==="unconfirmed" ? "unconfirmed" : null, activeStep:key==="working" ? 2 : null, decisionRejected:key==="rejected", runOverrides:{[configs[key].calls]:({working:"running",unknown:"needs_review",unconfirmed:"unconfirmed",rejected:"failed"})[key] || "delivered"}};
  };
  const badge = (label,tone="grey") => `<span class="badge ${tone}">${esc(label)}</span>`;
  const statusBadge = status => badge(...(statuses[status] || [status,"grey"]));
  const avatar = (member,tiny=false) => `<span class="avatar ${member.tone} ${tiny ? "tiny" : ""}">${member.short}</span>`;
  const tasks = () => state.tasks.map((status,index) => ({...taskDefinitions[index],status,runId:state.taskRunIds?.[index] || (status === "pending" || status === "dependent" ? null : "design-run-"+(index<2 ? index+2 : 5))}));
  const artifacts = () => publicData.artifacts.slice(0,state.artifacts);
  const activeMembers = () => state.memberCount ? members : [];
  const taskOwner = task => members[task.member === "A" ? 0 : 1];
  const events = () => {
    const list = publicData.steps.slice(1,state.activity+1).map((step,index) => ({id:"design-event-"+(index+1),type:index===0 || index===3 || index===5 ? "decision" : "work",title:step.event,description:`fixture 情景 · 状态 v${step.version}`,time:`10:${String(10+index*2).padStart(2,"0")}`,task:index===1 ? "work-one" : index===2 ? "work-two" : index===4 ? "work-followup" : null}));
    if (["running","unconfirmed"].includes(state.tasks[1]) && list.length) list[list.length-1] = {id:"design-event-active",type:"execution",title:"成员 B 开始执行依赖工作",description:state.live,time:"10:15",task:"work-two"};
    if (state.uncertain === "unknown" && list.length) list[list.length-1] = {id:"design-event-unknown",type:"execution",title:"成员 B 的执行结果未知",description:"进程中断，原执行进入核对状态（设计模拟）",time:"10:15",task:"work-two"};
    if (state.decisionRejected && list.length) list[list.length-1] = {id:"design-decision-rejected",type:"decision",title:"后续决定已拒绝",description:"原因：决定版本冲突，正式工作未新增（设计模拟）",time:"10:16",task:null,rejected:true};
    return [...list,...state.extraEvents].reverse();
  };
  function empty(title,copy,clear=false){return `<div class="empty-state"><div class="empty-glyph" aria-hidden="true">◇</div><strong>${esc(title)}</strong><p>${esc(copy)}</p>${clear ? '<button class="text-button" data-action="clear-filters">清空筛选</button>' : ""}</div>`;}
  const navLink = (key,text) => `<button class="text-button" data-action="navigate" data-key="${key}">${esc(text)} <span aria-hidden="true">→</span></button>`;
  const heading = (title,action="",note="") => `<div class="card-header"><h2>${esc(title)}</h2>${action || `<small>${esc(note)}</small>`}</div>`;
  function taskTable(list){
    if(!list.length) return empty(tasks().length ? "没有匹配的工作" : "尚未派发工作",tasks().length ? "调整搜索或筛选条件，查看其他工作。" : "组织安排提交后，工作才成为正式记录。",!!tasks().length);
    return `<div class="table-wrap"><table class="task-table"><thead><tr><th>工作与依赖</th><th class="owner-col">责任成员</th><th>状态</th></tr></thead><tbody>${list.map(task => `<tr data-task="${esc(task.id)}"><td><button class="task-name" data-action="task" data-id="${esc(task.id)}">${esc(task.title)}</button><div class="task-id">${esc(task.id)}</div>${task.index>0 ? `<button class="inline-dependency" data-action="task" data-id="${task.index===1 ? "work-one" : "work-two"}">↳ ${task.index===1 ? "依赖 work-one" : "依据已交付成果"}</button>` : '<div class="dependency-small">无前置依赖</div>'}</td><td class="owner-col"><div class="task-owner">${avatar(taskOwner(task),true)}成员 ${task.member}</div></td><td>${statusBadge(task.status)}</td></tr>`).join("")}</tbody></table></div>`;
  }
  const artifactRows = () => artifacts().length ? `<div class="artifact-list">${artifacts().map((item,index) => `<button class="artifact-row" data-action="artifact" data-id="${index}"><span class="file-icon">MD</span><span class="artifact-copy"><strong>${esc(item.name)}</strong><small>${esc(item.work_id)} · 版本 v${item.version} · fixture</small></span><span class="artifact-arrow" aria-hidden="true">↗</span></button>`).join("")}</div>` : empty("暂无成果","完成声明需要实际保存且可校验的文件。");
  const eventTimeline = list => list.length ? `<ol class="timeline">${list.map(item => `<li class="timeline-item"><div class="timeline-title"><span>${esc(item.title)} ${item.rejected ? badge("已拒绝","red") : ""}</span><time>${item.time}</time></div><p>${esc(item.description)}</p>${item.task ? `<button class="text-button" data-action="task" data-id="${esc(item.task)}">查看关联工作 →</button>` : `<button class="text-button" data-action="event" data-id="${esc(item.id)}">查看记录 →</button>`}</li>`).join("")}</ol>` : empty("暂无匹配的活动","调整类型筛选，或等待组织产生新的事件。");
  function overview(){
    const done=tasks().filter(task=>task.status==="delivered").length;
    return `<section class="card status-hero"><div class="status-top"><div class="eyebrow">SHARED GOAL / 共同目标</div>${badge(state.title,state.tone)}</div><h2>${esc(state.goal || "一个持续经营线上内容品牌的 AI 内容工作室。")}</h2><p class="status-description">目标保持连续，组织依据行动结果形成下一轮安排。</p><div class="status-bottom"><div class="status-item"><span class="status-icon" aria-hidden="true">◎</span><div><strong>现在发生了什么</strong><p>${esc(state.now)}</p><small>${esc(state.live)}${state.connected ? "" : " · 来自过期快照"}</small></div></div><div class="status-item"><span class="status-icon" aria-hidden="true">↗</span><div><strong>下一步</strong><p>${esc(state.next)}</p><small>依据当前模拟状态，不触发任何执行</small></div></div></div></section>
      <section class="metrics" aria-label="模拟组织指标">${[["组织成员",activeMembers().length,"名成员","岗位与稳定身份","◈"],["工作交付",done,"/ "+tasks().length,"包含跨成员成果依赖","▤"],["可读取成果",state.artifacts-(state.unavailable ? 1 : 0),"份文本",state.unavailable ? "另有 1 份校验失败（模拟）" : "模拟文件 · 来源可追溯","▱"],["调用占用",state.calls,"/ "+state.max,"fixture · 真实模型调用 0","↗"]].map(row => `<div class="card metric"><div class="metric-label">${row[0]}<span class="metric-symbol" aria-hidden="true">${row[4]}</span></div><div class="metric-number"><strong>${row[1]}</strong><span>${row[2]}</span></div><small>${row[3]}</small></div>`).join("")}</section>
      <div class="overview-grid"><div class="column"><section class="card">${heading("工作与依赖",navLink("tasks","查看全部工作"))}${taskTable(tasks())}<div class="card-foot"><span>责任与依赖来自设计模拟</span><span>${done} / ${tasks().length} 项已交付</span></div></section><section class="card">${heading("最近活动",navLink("activity","完整时间线"))}${eventTimeline(events().slice(0,3))}</section></div><div class="column"><section class="card">${heading("协作成员",navLink("members","组织结构"))}${activeMembers().length ? `<div class="member-list">${members.map(member => `<button class="member-row" data-action="member" data-id="${member.id}">${avatar(member)}<span class="member-copy"><strong>${member.name}</strong><small>${member.role} · fixture</small></span><span class="member-state">${tasks().some(task=>task.member===member.short && task.status==="running") ? "模拟执行中" : "已任职"}</span></button>`).join("")}</div>` : empty("尚无成员","有效启动决定后显示成员与任职。")}<div class="card-foot"><span>岗位由组织决定形成</span><span>章程 v${state.charterVersion}</span></div></section><section class="card">${heading("已保存成果",navLink("artifacts","全部成果"))}${artifactRows()}</section></div></div>`;
  }
  function membersView(){return activeMembers().length ? `<div class="cards-grid">${members.map(member => `<section class="card member-card"><div class="member-card-top">${avatar(member)}<div><h2>${member.name}</h2><small>${member.id}</small></div></div><dl><div><dt>岗位</dt><dd>${member.role}</dd></div><div><dt>任职</dt><dd>${member.assignment}</dd></div><div><dt>负责工作</dt><dd>${tasks().filter(task=>task.member===member.short).length} 项</dd></div><div><dt>来源</dt><dd>${badge("Fixture · 模拟","purple")}</dd></div></dl><p class="member-card-note">${member.description}</p><button class="button secondary" data-action="member" data-id="${member.id}">查看成员与工作 →</button></section>`).join("")}</div>` : `<section class="card">${empty("组织尚未形成","正式成员与岗位将在有效组织决定后出现。")}</section>`;}
  const taskView = () => `<section class="card"><div class="task-tools"><label class="search-box"><span aria-hidden="true">⌕</span><input id="task-search" placeholder="搜索工作标题或 ID" aria-label="搜索工作" value="${esc(query)}"></label><span class="filter-label">状态</span><select id="task-filter" aria-label="按状态筛选工作">${[["all","全部状态"],["delivered","已交付"],["running","执行中"],["dependent","等待依赖"],["pending","待执行"],["needs_review","待核对"],["unconfirmed","活性未确认"]].map(([value,label])=>`<option value="${value}" ${value===taskFilter ? "selected" : ""}>${label}</option>`).join("")}</select><select id="member-filter" aria-label="按成员筛选工作">${[["all","全部成员"],["A","成员 A"],["B","成员 B"]].map(([value,label])=>`<option value="${value}" ${value===memberFilter ? "selected" : ""}>${label}</option>`).join("")}</select></div><div id="filtered-tasks"></div><div class="card-foot"><span id="task-result-count"></span><span>设计情景 · 不派发工作</span></div></section>`;
  function renderFilteredTasks(){const list=tasks().filter(task=>(taskFilter==="all" || task.status===taskFilter) && (memberFilter==="all" || task.member===memberFilter) && (task.id+task.title).toLowerCase().includes(query.toLowerCase()));$("filtered-tasks").innerHTML=taskTable(list);$("task-result-count").textContent=`${list.length} / ${tasks().length} 项工作`;}
  const artifactView = () => artifacts().length ? `<div class="cards-grid">${artifacts().map((item,index)=>`<section class="card artifact-card"><div class="artifact-card-top"><span class="file-icon">MD</span>${item.name===state.unavailable ? badge("校验失败 · 模拟","red") : badge("公开 fixture","purple")}</div><h2>${esc(item.name)}</h2><p>${esc(item.work_id)}</p><div class="artifact-card-meta"><span>版本 v${item.version}</span><span>文本文件</span><span>${item.name===state.unavailable ? "SHA-256 未通过" : "SHA-256 已记录"}</span></div><button class="button secondary" data-action="artifact" data-id="${index}">${item.name===state.unavailable ? "查看校验错误与来源" : "查看内容与来源 ↗"}</button></section>`).join("")}</div>` : `<section class="card">${empty("还没有成果","任务交付后，查看实际保存的文件与来源。")}</section>`;
  const activityView = () => `<section class="card activity-full">${heading("组织活动","","全部时间与活动为设计模拟")}<div class="segmented" aria-label="活动类型">${[["all","全部活动"],["work","工作"],["decision","决定"],["execution","执行"],["event","事件"]].map(([key,label])=>`<button class="segment ${eventFilter===key ? "active" : ""}" aria-pressed="${eventFilter===key}" data-action="activity-filter" data-key="${key}">${label}</button>`).join("")}</div>${eventTimeline(events().filter(item=>eventFilter==="all" || item.type===eventFilter).slice(0,visibleEvents))}<div class="card-foot"><span>${Math.min(visibleEvents,events().filter(item=>eventFilter==="all" || item.type===eventFilter).length)} 条显示 · 设计模拟</span><button class="text-button" data-action="more-events" ${visibleEvents>=events().filter(item=>eventFilter==="all" || item.type===eventFilter).length ? "disabled" : ""}>显示更多 ↓</button></div></section>`;
  function resourcesView(){const runs=Array.from({length:state.calls},(_,index)=>({id:"design-run-"+(index+1),name:state.runNames?.[index+1] || (index===0 ? "形成组织安排" : index===1 ? "生成模拟资料" : index===2 ? "使用依赖成果" : index===3 ? "依据成果形成决定" : index===4 ? "执行后续工作" : "登记持久等待"),status:state.runOverrides?.[index+1] || (index===state.calls-1 && scenario==="working" ? "running" : index===state.calls-1 && scenario==="unknown" ? "needs_review" : index===state.calls-1 && scenario==="unconfirmed" ? "unconfirmed" : index===state.calls-1 && scenario==="rejected" ? "failed" : "delivered"),task:Object.hasOwn(state.runTasks || {},index+1) ? state.runTasks[index+1] : index===1 ? "work-one" : index===2 ? "work-two" : index===4 ? "work-followup" : null}));return `<div class="resource-grid"><section class="card">${heading("调用额度",state.calls>=state.max ? badge("额度耗尽","amber") : badge("有限资源","purple"))}<div class="budget-box"><div class="budget-number">${state.calls}<span>/ ${state.max} 次</span></div><progress class="budget-progress" aria-label="模拟调用占用" max="${state.max}" value="${state.calls}"></progress><div class="budget-caption"><span>累计占用，失败调用也保留</span><span>${state.max-state.calls} 次剩余</span></div><p class="resource-note">以上为设计模拟。首版运行时以调用数及单次超时限制执行；网页读取不占用调用额度。</p></div></section><section class="card">${heading("可核验回执","","不估造缺失数据")}<div class="receipt-values"><div><span>真实模型调用</span><strong>0 次</strong></div><div><span>模型 token 回执</span><strong>未提供</strong></div><div><span>金额费用</span><strong>未知</strong></div></div></section></div><section class="card">${heading("执行记录","","fixture / 设计模拟")}<div class="run-list">${runs.length ? runs.map(run=>`<div class="run-row"><span class="avatar tiny human">↗</span><div class="run-info">${run.task ? `<button class="task-name" data-action="task" data-id="${run.task}">${run.name}</button>` : `<strong>${run.name}</strong>`}<small>${run.id} · fixture · 模拟</small></div><div class="run-meta">时间为设计情景<br>不来自实际进程</div>${statusBadge(run.status)}</div>`).join("") : empty("尚无执行","组织调用记录将在有效派发后出现。")}</div><div class="card-foot"><span>${esc(state.live)}</span><span>费用未知</span></div></section>`;}
  function render(){
    $("navigation").innerHTML=Object.entries(pages).map(([key,value])=>`<button class="nav-button ${key===pageKey ? "active" : ""}" data-action="navigate" data-key="${key}" ${key===pageKey ? 'aria-current="page"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true">${icons[key]}</svg><span>${value[0]}</span>${key==="tasks" ? `<span class="nav-count">${tasks().length}</span>` : ""}</button>`).join("");
    $("breadcrumb-page").textContent=pages[pageKey][0];$("page-title").textContent=pages[pageKey][1];$("page-description").textContent=pages[pageKey][2];
    $("connection-label").textContent=state.connected ? "连接情景：正常（模拟）" : "连接情景：断开 · 快照过期";
    $("connection-dot").className="dot "+(state.connected ? "green" : "amber");$("last-updated").textContent="原型刷新 "+acceptedTime;
    $("connection-warning").hidden=state.connected;$("state-version").textContent="状态 v"+state.version;$("snapshot-order").textContent="模拟快照 #"+sequence;
    $("org-name").textContent=state.name;$("org-id").textContent=state.orgId;
    $("view").innerHTML=({overview,members:membersView,tasks:taskView,artifacts:artifactView,activity:activityView,resources:resourcesView,settings:()=>window.UNION_CONSOLE_SETTINGS?.(state) || ""}[pageKey])();
    if(pageKey==="tasks") renderFilteredTasks();
    window.UNION_DESIGN_STATE={scenario,page:pageKey,version:state.version,sequence,pending_events:state.extraEvents.length,connected:state.connected,real_model_calls:0};
    document.dispatchEvent(new Event("union-design-render"));
  }
  const clock = () => new Intl.DateTimeFormat("zh-CN",{timeZone:"Asia/Shanghai",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).format(new Date());
  function notify(message){clearTimeout(toastTimer);$("toast").textContent=message;$("toast").hidden=false;toastTimer=setTimeout(()=>{$("toast").hidden=true;},2500);}
  function applySnapshot(snapshot,order){if(order<=sequence)return false;sequence=order;state=structuredClone(snapshot);acceptedTime=clock();render();return true;}
  function acceptSnapshot(){applySnapshot(state,sequence+1);}
  function navigate(key){if(!pages[key])return;if($("detail-dialog").open)$("detail-dialog").close();pageKey=key;render();$("main").focus({preventScroll:true});}
  const detailPair = (label,value) => `<div><dt>${esc(label)}</dt><dd>${value}</dd></div>`;
  function openDetail(kind,id){
    let title="",body="",category="",content=null;
    if(kind==="task"){
      const task=tasks().find(item=>item.id===id);if(!task){notify("当前情景尚未创建这项工作。");return;}
      title=task.title;category="WORK / 工作详情";
      const associated=artifacts().filter(item=>item.work_id===task.id);
      body=`<dl class="detail-dl">${detailPair("工作 ID",esc(task.id))}${detailPair("状态",statusBadge(task.status))}${detailPair("责任成员",esc(taskOwner(task).name))}${detailPair("岗位",esc(taskOwner(task).role))}${detailPair("执行 ID",esc(task.runId || "尚未派发"))}${detailPair("来源",badge("Fixture · 设计模拟","purple"))}</dl><section class="detail-section"><h3>工作说明</h3><p>${esc(task.instruction)}</p></section><section class="detail-section"><h3>依赖资料</h3>${task.index ? `<div class="detail-links"><button class="button secondary" data-action="task" data-id="${task.index===1 ? "work-one" : "work-two"}">查看前置工作 →</button>${artifacts().length ? '<button class="button secondary" data-action="artifact" data-id="0">读取 source.md ↗</button>' : ""}</div>` : "<p>无前置依赖。</p>"}</section><section class="detail-section"><h3>已关联成果</h3><div class="detail-links">${associated.length ? associated.map(item=>`<button class="button secondary" data-action="artifact" data-id="${artifacts().indexOf(item)}">${esc(item.name)} ↗</button>`).join("") : "<p>尚未交付成果。</p>"}</div></section><section class="detail-section"><h3>决定与记录</h3><p>组织决定为工作指定责任与依据；此原型只展示设计关联。</p><div class="detail-links"><button class="button secondary" data-action="navigate" data-key="activity">查看活动时间线 →</button><button class="button secondary" data-action="member" data-id="${taskOwner(task).id}">查看责任成员 →</button></div></section>`;
    }else if(kind==="artifact"){
      const item=artifacts()[Number(id)];if(!item)return;title=item.name;category="ARTIFACT / 模拟成果";const usable=item.name!==state.unavailable;content=usable ? item.content : null;
      body=`<dl class="detail-dl">${detailPair("关联工作",esc(item.work_id))}${detailPair("版本","v"+item.version)}${detailPair("责任成员",item.work_id==="work-one" ? "测试成员 A" : "测试成员 B")}${detailPair("来源",badge("公开 fixture","purple"))}</dl>${usable ? '<pre id="artifact-text"></pre>' : '<div class="connection-warning">成果文件校验失败（设计情景）。内容未展示；历史交付记录保留。</div>'}<span class="hash">SHA-256 ${esc(item.sha256)}</span><div class="download-area"><small>内置公开文本 · 无真实发布</small>${usable ? `<a id="download-artifact" class="button primary" download="${esc(item.name)}">下载模拟成果 ↓</a>` : '<button id="download-artifact" class="button secondary" disabled>下载不可用</button>'}</div><section class="detail-section"><div class="detail-links"><button class="button secondary" data-action="task" data-id="${esc(item.work_id)}">查看来源工作 →</button></div></section>`;
    }else if(kind==="member"){
      const member=members.find(item=>item.id===id);if(!member)return;title=member.name;category="MEMBER / 身份与责任";
      body=`<dl class="detail-dl">${detailPair("稳定身份",esc(member.id))}${detailPair("岗位",esc(member.role))}${detailPair("当前任职",esc(member.assignment))}${detailPair("来源",badge("Fixture · 设计模拟","purple"))}</dl><section class="detail-section"><h3>职责</h3><p>${esc(member.description)}</p></section><section class="detail-section"><h3>负责工作</h3><div class="detail-links">${tasks().filter(task=>task.member===member.short).map(task=>`<button class="button secondary" data-action="task" data-id="${task.id}">${esc(task.title)} →</button>`).join("") || "<p>尚无工作。</p>"}</div></section><section class="detail-section"><h3>交接</h3><p>当前设计情景没有发生交接。生产视图须依据历史任职显示交接关系，不能编造历史。</p></section>`;
    }else if(kind==="event"){
      const item=events().find(event=>event.id===id);if(!item)return;title=item.title;category="EVENT / 活动记录";
      body=`<dl class="detail-dl">${detailPair("设计记录 ID",esc(item.id))}${detailPair("类型",item.type==="decision" ? "组织决定" : "外部事件")}${detailPair("状态",item.rejected ? badge("已拒绝","red") : badge("已记录","purple"))}${detailPair("来源","设计模拟")}</dl><section class="detail-section"><h3>依据与说明</h3><p>${esc(item.description)}</p></section><section class="detail-section"><p>此记录为原型情景，并非实际数据库回执。</p></section>`;
    }
    if(!title)return;$("detail-title").textContent=title;$("detail-category").textContent=category;$("detail-body").innerHTML=body;
    if(content!==null){$("artifact-text").textContent=content;$("download-artifact").href="data:text/plain;charset=utf-8,"+encodeURIComponent(content);}
    if(!$("detail-dialog").open)$("detail-dialog").showModal();
  }
  document.addEventListener("click",event=>{
    const button=event.target.closest("[data-action]");if(!button || button.disabled)return;
    const {action,key,id}=button.dataset;
    if(action==="navigate")navigate(key);
    else if(["task","artifact","member","event"].includes(action))openDetail(action,id);
    else if(action==="clear-filters"){query="";taskFilter="all";memberFilter="all";render();}
    else if(action==="activity-filter"){eventFilter=key;visibleEvents=5;render();}
    else if(action==="more-events"){visibleEvents+=5;render();}
  });
  document.addEventListener("input",event=>{if(event.target.id==="task-search"){query=event.target.value;renderFilteredTasks();}});
  document.addEventListener("change",event=>{if(event.target.id==="task-filter"){taskFilter=event.target.value;renderFilteredTasks();}if(event.target.id==="member-filter"){memberFilter=event.target.value;renderFilteredTasks();}});
  $("scenario").addEventListener("change",()=>{
    clearTimeout(toastTimer);$("toast").hidden=true;
    if($("detail-dialog").open)$("detail-dialog").close();
    const selected=$("scenario").value;
    if(selected==="disconnected"){state.connected=false;render();}else{scenario=selected;state=initial(scenario);query="";taskFilter=memberFilter="all";eventFilter="all";visibleEvents=5;acceptSnapshot();}
  });
  $("refresh").addEventListener("click",()=>{if(!state.connected){notify("原型仍处于断开情景；选择其他情景演示恢复。");return;}acceptSnapshot();notify("已刷新模拟快照；没有访问真实服务。");});
  $("same-version").addEventListener("click",()=>{if(!state.connected){$("tool-feedback").textContent="断开情景不接受新的模拟快照。";return;}state.extraEvents.push({id:"design-added-"+(sequence+1),type:"event",title:"同版本新增模拟事件",description:"组织版本未变，事件列表仍须更新。",time:clock(),task:null});acceptSnapshot();$("tool-feedback").textContent=`状态仍为 v${state.version}，已更新到模拟快照 #${sequence}。`;});
  $("old-response").addEventListener("click",()=>{const stale={...state,connected:false,extraEvents:[],calls:0};const accepted=applySnapshot(stale,sequence-1);$("tool-feedback").textContent=accepted ? "旧响应被错误接受。" : `已丢弃旧模拟响应。快照 #${sequence}、状态 v${state.version}、连接与时间均保持当前值。`;});
  $("reset-design").addEventListener("click",()=>{clearTimeout(toastTimer);$("toast").hidden=true;scenario="working";state=initial(scenario);pageKey="overview";query="";taskFilter=memberFilter="all";eventFilter="all";visibleEvents=5;$("scenario").value="working";$("tool-feedback").textContent="";acceptSnapshot();});
  $("close-dialog").addEventListener("click",()=>$("detail-dialog").close());
  $("detail-dialog").addEventListener("click",event=>{const box=$("detail-dialog").getBoundingClientRect();if(event.target===$("detail-dialog") && (event.clientX<box.left || event.clientX>box.right || event.clientY<box.top || event.clientY>box.bottom))$("detail-dialog").close();});
  document.querySelector(".brand").addEventListener("click",()=>navigate("overview"));
  window.UNION_DESIGN_API={read:()=>structuredClone(state), update:next=>{scenario="console";state=structuredClone(next);acceptSnapshot();}, initial, navigate, render, notify};
  state=initial(scenario);acceptSnapshot();
})();
