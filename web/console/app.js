"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const pretty = value => esc(JSON.stringify(value, null, 2));
  const pages = {overview:["总览","组织总览","从当前行动，到下一轮决定。"],members:["成员与岗位","成员与岗位","稳定身份、明确责任，以及可以延续的协作。"],tasks:["工作","工作与依赖","每项工作都有责任人、依据与可追溯的结果。"],artifacts:["成果","组织成果","读取实际文件，核对版本与来源。"],activity:["活动","事件与决定","当前安排如何形成，后续行动因何发生。"],resources:["执行与资源","执行与资源","调用有边界，未知费用如实显示。"],settings:["组织设置","组织设置与回执","采用规则、调整资源，并确认操作结果。"]};
  const titles = {create:"创建并采用组织",start:"启动／继续有限运行",pause:"暂停新的派发",event:"提交组织事件",resources:"调整资源",amend:"修订组织章程",reconcile:"核对未知执行"};
  const labels = {bootstrap:"组织尚未形成",execute_work:"等待派发工作",decide:"等待组织决定",wait:"等待新事件",running:"协作进行中",unconfirmed:"执行活性未确认",unknown:"执行待核对",blocked:"运行受阻",paused:"派发已暂停",pause_requested:"暂停已请求，等待在途回执",needs_review:"执行待核对",dependent:"等待依赖",pending:"待执行",delivered:"已交付",failed:"执行失败",cancelled:"已取消",reconciled:"已核对",accepted:"已受理",rejected:"已拒绝",succeeded:"已完成",idle:"无在途执行",enabled:"允许派发"};
  const sourceName = source => ({fixture:"Fixture · 模拟",real:"真实执行记录",mixed:"模拟与真实混合",not_run:"尚未执行"}[source] || source);
  const defaultCharter = {text:"本地有限组织试验。组织在已配置资源内形成岗位和协作；无对外发布或支付权限。",allowed_operations:["create_member","create_position","update_position","assign","set_policy","create_work","handoff","pause_work","resume_work","cancel_work","update_work","wait","set_strategy","record_memory"],allowed_tools:["produce_artifact"],reserved_matters:["goal","resources","charter","funding","dissolution"],board_can_amend:true};
  let session = null, data = null, orgId = "", page = "overview", connected = false, lastSuccess = "";
  let epoch = 0, serial = 0, controller, latestInstance = "", lastSequence = -1, offset = 0, detailSerial = 0;
  let query = "", workFilter = "all", memberFilter = "all", activityFilter = "all", draft = null;
  let pending;
  const confirmedReceipts=new Map();
  try { pending = JSON.parse(sessionStorage.getItem("union-pending") || "[]"); } catch { pending = []; }
  const savePending = () => sessionStorage.setItem("union-pending", JSON.stringify(pending));
  const badge = value => `<span class="badge ${["delivered","succeeded"].includes(value) ? "green" : ["unknown","failed","rejected","needs_review"].includes(value) ? "red" : ["wait","paused","dependent","unconfirmed","blocked","pause_requested"].includes(value) ? "amber" : "purple"}">${esc(labels[value] || value)}</span>`;
  const empty = (title, message) => `<div class="empty-state"><strong>${esc(title)}</strong><p>${esc(message)}</p></div>`;
  const link = (kind,id,label) => `<button class="task-name" data-detail="${kind}" data-id="${esc(id)}">${esc(label)}</button>`;
  const panel = (title,content) => `<section class="card console-card"><h2>${esc(title)}</h2>${content}</section>`;
  const works = () => Object.values(data?.organization.work || {});
  const members = () => Object.values(data?.organization.members || {});
  const artifacts = () => Object.values(data?.organization.artifacts || {});
  const memberName = id => data?.organization.members[id]?.name || id || "尚未任职";
  const errorText = e => e.name === "AbortError" ? "请求超时，请刷新或查询原回执" : e.message || "服务暂不可用";
  function notify(message) { $("toast").textContent=message; $("toast").hidden=false; setTimeout(()=>$("toast").hidden=true,4500); }

  async function api(path, options={}, signal) {
    const local = signal ? null : new AbortController();
    const timer = local ? setTimeout(()=>local.abort(),5000) : null;
    try {
      const response = await fetch(path,{credentials:"same-origin",cache:"no-store",...options,signal:signal || local.signal});
      const value = await response.json();
      if(!response.ok) { const error = new Error(value.error || "请求未成功"); error.status=response.status; throw error; }
      return value;
    } finally { if(timer)clearTimeout(timer); }
  }

  function disconnected(message) {
    connected=false;
    $("connection-label").textContent="连接断开";
    $("connection-dot").className="dot amber";
    $("connection-warning").hidden=false;
    $("connection-warning").textContent=message + (data ? "。以下为最后成功快照，数据已过期；输入与原请求标识保留。" : "。尚无实时组织数据，请从本机启动链接连接。");
    controls();
  }

  async function refresh() {
    const request = ++serial, generation=epoch;
    if(controller)controller.abort();
    controller=new AbortController();
    const signal=controller.signal, timer=setTimeout(()=>controller.abort(),3500);
    try {
      const info=await api("/api/session",{},signal);
      if(request!==serial || generation!==epoch)return;
      let target=orgId;
      if(!info.organizations.some(o=>o.id===target))target=info.organizations[0]?.id || "";
      const result=target ? await api(`/api/snapshot?organization_id=${encodeURIComponent(target)}&offset=${offset}`,{},signal) : null;
      if(request!==serial || generation!==epoch)return;
      if(result && (result.service_instance!==info.service_instance || result.organization.id!==target))throw new Error("服务或组织已切换，请重新读取");
      if(result && latestInstance===result.service_instance && orgId===target && result.snapshot_sequence<=lastSequence)return;
      session=info; orgId=target;
      if(result) { data=result; latestInstance=result.service_instance; lastSequence=result.snapshot_sequence; }
      else data=null;
      connected=true; lastSuccess=new Date().toLocaleTimeString("zh-CN",{hour12:false});
      $("connection-label").textContent="已连接本机服务"; $("connection-dot").className="dot green";
      $("connection-warning").hidden=true; $("last-updated").textContent="最后成功 " + lastSuccess;
      $("role-label").textContent=info.role==="board" ? "本机发起人" : "本机观察者";
      $("org-select").innerHTML=info.organizations.length ? info.organizations.map(o=>`<option value="${esc(o.id)}" ${o.id===orgId ? "selected" : ""}>${esc(o.name)}</option>`).join("") : '<option value="">尚未创建组织</option>';
      render();
      await queryPending();
    } catch(error) {
      if(request===serial && generation===epoch)disconnected(errorText(error));
    } finally { clearTimeout(timer); }
  }

  function blocked(kind) {
    if(!connected)return "连接断开，先读取最新状态";
    if(session?.role!=="board")return "观察者可查看，操作需要发起人会话";
    if(kind==="create")return "";
    if(!data)return "请先创建组织";
    if(kind==="start") {
      if(data.execution_state==="running" || data.host_activity.confirmed)return "已有运行作业，不能重复启动";
      if(data.execution_state==="unknown")return "执行结果未知，请先核对";
      if(data.budget.blocked_reason)return data.budget.blocked_reason;
    }
    if(["amend","resources","reconcile"].includes(kind) && data.host_activity.confirmed)return "先暂停派发并等待在途回执";
    if(kind==="amend" && !data.charter.board_can_amend)return "现行章程不允许此修订入口";
    if(kind==="reconcile" && !data.runs.some(r=>r.status==="unknown"))return "仅能核对已确认 unknown 的执行";
    return "";
  }
  const commandButton = (kind,label,primary=false) => `<button class="button ${primary ? "primary" : "secondary"}" data-command="${kind}" ${blocked(kind) ? `disabled title="${esc(blocked(kind))}"` : ""}>${esc(label)}</button>`;
  function controls() {
    $("console-controls").innerHTML=`<div class="console-buttons">${commandButton("create","＋ 新建组织")}${commandButton("start","启动／继续",true)}${commandButton("pause","暂停派发")}${commandButton("event","提交事件")}${data?.execution_state==="unknown" ? commandButton("reconcile","核对执行") : ""}</div><p class="console-hint">${esc(!connected ? "连接断开：保留快照与输入，恢复后查询原回执。" : session?.role!=="board" ? "观察者会话：可读取与下载，不能提交组织操作。" : data?.dispatch_state==="pause_requested" ? labels.pause_requested : "操作先预览，再提交。受理后的实际结果保存在操作回执中。")}</p>${pending.filter(p=>!p.organization_id || p.organization_id===orgId).map(p=>`<p class="console-hint">请求 ${esc(p.id)} 尚待最终回执 <button class="text-button" data-query-receipt="${esc(p.id)}">查询原请求</button></p>`).join("")}`;
    if(draft && !draft.submitted)$("commit-operation").disabled=!!blocked(draft.kind);
  }

  function workRows(list) {
    return list.length ? `<div class="runtime-list">${list.map(w=>`<article class="runtime-row"><div>${link("work",w.id,w.title)}<small>${esc(w.id)} · ${esc(memberName(w.member_id))}</small>${w.dependencies.length ? `<p class="state-note">依赖 ${w.dependencies.map(d=>link("work",d,data.organization.work[d]?.title || d)).join("、")}</p>` : ""}</div>${badge(w.display_status)}</article>`).join("")}</div>` : empty("没有匹配的工作","可以清空筛选，或等待组织形成正式工作。");
  }
  function artifactRows(list=artifacts()) {
    return list.length ? list.map(a=>`<article class="runtime-row"><span class="file-icon">TXT</span><div>${link("artifact",a.id,a.name)}<small>版本 ${a.version} · ${esc(memberName(a.member_id))} · ${esc(a.work_id)}</small></div><span class="badge purple">打开时校验</span></article>`).join("") : empty("还没有成果","工作交付后，可读取实际文件与版本。");
  }
  function overview() {
    const state=data.organization;
    const stage=data.dispatch_state==="pause_requested" ? "pause_requested" : data.next_step;
    return `<section class="status-hero"><div class="eyebrow">${esc(state.name)} · ${esc(sourceName(data.source))}</div><h2>${esc(labels[stage] || stage)}</h2><p class="status-description">${esc(state.goal)}</p><div class="status-bottom"><div class="status-item"><span>当前行动</span><p>${esc(data.runs.filter(r=>r.status==="running").map(r=>r.work_id || "组织决定").join("、") || labels[data.next_step])}</p></div><div class="status-item"><span>下一步与复查</span><p>${esc(data.blocked_reasons.join("；") || (data.next_review_at ? "复查时间 " + data.next_review_at : "按待办与新事件继续；暂无定时复查"))}</p></div></div></section><section class="metrics">${[["正式成员",members().length,"人"],["工作",works().length,"项"],["成果版本",artifacts().length,"份"],["调用占用",data.budget.calls_reserved,"次"]].map(([title,count,unit])=>`<div class="metric"><div class="metric-label">${title}</div><div class="metric-number"><strong>${count}</strong><span>${unit}</span></div><small>${esc(sourceName(data.source))}</small></div>`).join("")}</section><div class="overview-grid"><div class="column">${panel("工作与依赖",workRows(works()))}</div><div class="column">${panel("协作成员",memberRows())}${panel("已保存成果",artifactRows())}</div></div>`;
  }
  function memberRows() {
    return members().length ? members().map(m=>`<article class="runtime-row"><span class="avatar">${esc(m.name.slice(0,1))}</span><div>${link("member",m.id,m.name)}<small>${esc(m.id)} · ${works().filter(w=>w.member_id===m.id).length} 项工作</small></div></article>`).join("") : empty("组织尚未形成","有效启动决定后显示成员与任职。");
  }
  function membersView() {
    return panel("成员与当前任职",memberRows()) + panel("岗位与责任",Object.values(data.organization.positions).map(p=>`<article class="runtime-row"><div><strong>${esc(p.title)}</strong><small>${esc(p.id)} · v${p.version}</small><p>${esc(p.mandate)}</p>${Object.values(data.organization.assignments).filter(a=>a.position_id===p.id).map(a=>`<p>${link("member",a.member_id,memberName(a.member_id))} · ${a.active ? "当前任职" : "历史任职／已交接"} · ${esc(a.id)}</p>`).join("")}</div></article>`).join("") || empty("尚无岗位","岗位由组织决定形成。"));
  }
  function tasksView() {
    return `<section class="card"><div class="task-tools"><label class="search-box"><input id="task-search" placeholder="搜索工作标题或 ID" aria-label="搜索工作" value="${esc(query)}"></label><select id="work-filter" aria-label="按状态筛选">${["all","pending","dependent","running","unconfirmed","delivered","blocked","failed","paused","needs_review","cancelled"].map(v=>`<option value="${v}" ${workFilter===v ? "selected" : ""}>${labels[v] || "全部状态"}</option>`).join("")}</select><select id="member-filter" aria-label="按成员筛选"><option value="all">全部成员</option>${members().map(m=>`<option value="${esc(m.id)}" ${memberFilter===m.id ? "selected" : ""}>${esc(m.name)}</option>`).join("")}</select><button class="text-button" data-clear>清空筛选</button></div><div class="console-card" id="filtered-work"></div></section>`;
  }
  function filterWork() { if($("filtered-work"))$("filtered-work").innerHTML=workRows(works().filter(w=>(workFilter==="all" || w.display_status===workFilter) && (memberFilter==="all" || w.member_id===memberFilter) && (w.title+w.id).toLowerCase().includes(query.toLowerCase()))); }
  function activityView() {
    let rows=[...data.events.map(e=>({...e,type:"event",title:e.kind})),...data.decisions.map(d=>({...d,type:"decision",title:d.data.issue}))];
    rows=rows.filter(r=>activityFilter==="all" || activityFilter===r.type).sort((a,b)=>b.created_at.localeCompare(a.created_at));
    return panel("事件与决定",`<div class="segmented">${[["all","全部"],["event","事件"],["decision","决定"]].map(([v,t])=>`<button class="segment ${activityFilter===v ? "active" : ""}" aria-pressed="${activityFilter===v}" data-activity="${v}">${t}</button>`).join("")}</div>${rows.map(r=>`<article class="runtime-row"><div>${link(r.type,r.id,r.title)}<small>${esc(r.created_at)} · ${esc(r.id)}</small></div>${r.status ? badge(r.status) : '<span class="badge grey">事件</span>'}</article>`).join("") || empty("暂无活动","有效操作、执行与组织决定在此留痕。")}<div class="toolbar-pages"><button class="button secondary" data-page="-1" ${offset===0 ? "disabled" : ""}>上一页</button><span>第 ${Math.floor(offset/50)+1} 页 · 每类最多 50 条</span><button class="button secondary" data-page="1" ${offset+50>=Math.max(data.pagination.event_count,data.pagination.decision_count) ? "disabled" : ""}>下一页</button></div>`);
  }
  function resourcesView() {
    return `<div class="resource-grid">${panel("调用额度",`<div class="budget-number">${data.budget.calls_reserved}<span> / ${data.budget.max_calls} 次</span></div><progress class="budget-progress" aria-label="累计调用占用" value="${data.budget.calls_reserved}" max="${data.budget.max_calls}"></progress><p>单次超时 ${data.organization.resources.timeout_seconds} 秒；失败和未知调用保留占用。</p>${commandButton("resources","调整资源")}`)}${panel("执行依据",`<p>执行来源：${esc(sourceName(data.source))}</p><p>宿主活性：${data.host_activity.confirmed ? "已确认" : "无有效活性依据"}</p><p>执行记录：${esc(labels[data.execution_state])}</p><p>派发状态：${esc(labels[data.dispatch_state])}</p><p>金额费用：未知</p>`)}</div>${panel("执行记录",data.runs.map(r=>`<article class="runtime-row"><div>${link("run",r.id,r.work_id || "组织决定")}<small>${esc(r.id)} · ${esc(r.executor)}${r.simulated ? " · 模拟" : " · 真实执行器"}</small><small>开始 ${esc(r.started_at)}<br>结束 ${esc(r.ended_at || "未结束")}</small></div>${badge(r.display_status)}</article>`).join("") || empty("尚无调用","读取和刷新不消耗调用额度。"))}`;
  }
  function receiptRows() {
    return data.receipts.map(r=>`<article class="command-receipt"><div>${link("receipt",r.id,titles[r.kind] || r.kind)}${badge(r.status)}</div><p>${esc(r.message)}</p><small>${esc(r.id)} · ${esc(r.actor)} · 基准 v${r.base_version} · ${esc(r.created_at)}</small></article>`).join("") || empty("暂无操作回执","提交操作后在此查询结果。");
  }
  function settingsView() {
    return `<div class="cards-grid">${panel("已采用章程 · v"+data.organization.charter_version,`<p class="charter-copy">${esc(data.charter.text)}</p><p>文本成果工具：${data.charter.allowed_tools.includes("produce_artifact") ? "允许" : "未授权"} · 当前修章入口：${data.charter.board_can_amend ? "允许" : "不允许"}</p>${commandButton("amend","预览修章")}<details><summary>受支持规则</summary><pre>${pretty(data.charter)}</pre></details>`)}${panel("资源与异常处理",`<p>已占用 ${data.budget.calls_reserved} / ${data.budget.max_calls} 次调用</p><p>单次 ${data.organization.resources.timeout_seconds} 秒；金额费用未知。</p>${commandButton("resources","调整资源")}${commandButton("reconcile","核对未知执行")}`)}</div>${panel("操作回执",receiptRows())}`;
  }
  function render() {
    const focus=document.activeElement?.id, start=document.activeElement?.selectionStart;
    $("navigation").innerHTML=Object.entries(pages).map(([key,value])=>`<button class="nav-button ${page===key ? "active" : ""}" data-nav="${key}" aria-current="${page===key ? "page" : "false"}"><span>${value[0]}</span></button>`).join("");
    $("page-title").textContent=pages[page][1]; $("breadcrumb-page").textContent=pages[page][0]; $("page-description").textContent=pages[page][2];
    $("source-label").textContent=data ? sourceName(data.source) : "尚未执行";
    controls();
    $("view").innerHTML=!data ? !session || orgId ? panel("连接本机组织",empty("正在读取组织","取得有效会话与快照后，显示组织的实际记录。")) : panel("从一个目标开始",empty("尚未创建组织","创建并采用章程后，再明确启动有限运行。创建不会自动调用模型。")) : ({overview,members:membersView,tasks:tasksView,artifacts:()=>panel("全部成果版本",artifactRows()),activity:activityView,resources:resourcesView,settings:settingsView}[page])();
    filterWork();
    $("snapshot-meta").textContent=data ? `${data.organization.id} · 状态 v${data.organization.version} · 章程 v${data.organization.charter_version} · 快照 ${data.snapshot_sequence} · 采集 ${data.collected_at}` : "尚无组织快照";
    if(focus && $(focus) && !$(focus).closest("dialog")) { $(focus).focus({preventScroll:true}); if(typeof start==="number" && $(focus).setSelectionRange)$(focus).setSelectionRange(start,start); }
  }

  async function detail(kind,id) {
    const serial=++detailSerial, organization=orgId;
    $("detail-title").textContent="正在读取详情"; $("detail-body").textContent="";
    if(!$("detail-dialog").open)$("detail-dialog").showModal();
    let title,body;
    if(kind==="artifact") {
      const a=data.organization.artifacts[id]; if(!a)return;
      title=a.name; body=`<p>正在读取文件并校验 SHA-256…</p>`;
      $("detail-title").textContent=title; $("detail-body").innerHTML=body;
      try {
        const result=await api(`/api/artifact?organization_id=${encodeURIComponent(organization)}&id=${encodeURIComponent(id)}`);
        if(serial!==detailSerial || organization!==orgId || !$("detail-dialog").open)return;
        body=`<p class="notice-source">${esc(sourceName(data.source))} · SHA-256 已校验 · v${a.version}</p><small>${esc(a.sha256)}</small><pre class="detail-data">${esc(result.content)}</pre><div class="detail-links">${link("work",a.work_id,"来源工作")}${link("member",a.member_id,"负责成员")}<a class="button primary" href="/api/artifact?organization_id=${encodeURIComponent(organization)}&id=${encodeURIComponent(id)}&download=1" download>下载已校验文件</a></div>`;
      } catch(error) { body=`<p class="operation-error">成果不可用：${esc(errorText(error))}</p><p>交付历史保留；不能将当前文件视为可用成果。</p>`; }
    } else if(kind==="work") {
      const w=data.organization.work[id]; if(!w)return;
      title=w.title; body=`${badge(w.display_status)}<p>${esc(w.instruction)}</p><dl class="detail-dl"><div><dt>负责成员</dt><dd>${link("member",w.member_id,memberName(w.member_id))}</dd></div><div><dt>工作版本与任职</dt><dd>v${w.version} · ${esc(w.assignment_id)}</dd></div></dl><p>${esc(w.summary || "尚无交付说明")}</p><div class="detail-links">${w.dependencies.map(d=>link("work",d,"依赖："+(data.organization.work[d]?.title || d))).join("")}${w.artifact_ids.map(a=>link("artifact",a,data.organization.artifacts[a]?.name || a)).join("")}${w.run_id ? link("run",w.run_id,"执行记录") : ""}</div><h3>关联决定</h3>${data.decisions.filter(d=>JSON.stringify(d.data.operations).includes('"'+id+'"')).map(d=>`<p>${link("decision",d.id,d.data.issue)}</p>`).join("") || '<p>当前页没有关联决定，可在活动中翻页查看。</p>'}`;
    } else if(kind==="member") {
      const m=data.organization.members[id]; if(!m)return;
      title=m.name; body=`<p>${esc(m.id)} · ${esc(sourceName(data.source))}</p>${Object.values(data.organization.assignments).filter(a=>a.member_id===id).map(a=>`<p>${esc(data.organization.positions[a.position_id]?.title)} · ${a.active ? "当前任职" : "历史任职／已交接"} · ${esc(a.id)}</p>`).join("")}${workRows(works().filter(w=>w.member_id===id))}`;
    } else {
      const row=({event:data.events,decision:data.decisions,run:data.runs,receipt:data.receipts}[kind] || []).find(r=>r.id===id); if(!row)return;
      title=kind==="run" ? "执行记录" : kind==="receipt" ? "操作回执" : kind==="event" ? "组织事件" : "组织决定";
      body=`${row.status ? badge(row.display_status || row.status) : ""}<pre class="detail-data">${pretty(row)}</pre>${kind==="run" ? `<p>输入 token：${row.usage?.input_tokens ?? "未提供"} · 输出 token：${row.usage?.output_tokens ?? "未提供"} · 金额未知</p>${row.work_id ? link("work",row.work_id,"关联工作") : ""}` : ""}`;
    }
    if(serial===detailSerial && organization===orgId) { $("detail-title").textContent=title; $("detail-body").innerHTML=body; }
  }

  const field = (name,label,value="",type="text",extra="") => `<label class="operation-field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra} required></label>`;
  const area = (name,label,value="",rows=3) => `<label class="operation-field">${esc(label)}<textarea name="${name}" rows="${rows}" required maxlength="100000">${esc(value)}</textarea></label>`;
  const reason = () => area("reason","操作理由与核对依据");
  const rules = charter => area("charter_text","章程正文",charter.text)+`<details><summary>受支持的规则字段</summary>${area("charter_rules","组织操作、工具、保留事项与修章入口",JSON.stringify({allowed_operations:charter.allowed_operations,allowed_tools:charter.allowed_tools,reserved_matters:charter.reserved_matters,board_can_amend:charter.board_can_amend},null,2),8)}<p class="form-note">只接受已实现的规则字段；正文不隐式授予权限。</p></details>`;
  function form(kind) {
    if(kind==="create")return field("name","组织名称","我的试验组织","text",'maxlength="200"')+area("goal","组织目标","一个持续经营线上内容品牌的 AI 内容工作室。")+field("board_name","章程采用人","本机发起人（本地测试采用）","text",'maxlength="200"')+rules(defaultCharter)+field("max_calls","累计调用上限",8,"number",'min="1" max="10000"')+field("timeout_seconds","单次超时（秒）",180,"number",'min="1" max="3600"');
    if(kind==="start")return `<p class="form-note">已占用 ${data.budget.calls_reserved} / ${data.budget.max_calls} 次；每次最多 ${data.organization.resources.timeout_seconds} 秒。${data.execution_state==="unconfirmed" ? "持久执行活性未确认：启动入口先取得互斥锁并检查原执行；遗留执行将进入 unknown，不会重派。" : ""}</p><label class="operation-field">执行器<select name="executor">${session.executors.map(e=>`<option value="${e}">${e==="fixture" ? "Fixture · 确定性模拟" : "Codex · 真实执行器，费用未知"}</option>`).join("")}</select></label>`+field("max_steps","本次最多执行步数",Math.min(8,data.budget.max_calls-data.budget.calls_reserved),"number",`min="1" max="${data.budget.max_calls-data.budget.calls_reserved}"`)+field("max_seconds","等待新事件窗口（秒，0 表示不持续等待）",0,"number",'min="0" max="86400"')+`<label class="check-field"><input type="checkbox" name="allow_unknown_cost">明确接受本次有限真实调用的费用未知条件。Fixture 不调用模型。</label>`;
    if(kind==="pause")return '<p class="form-note">提交后停止新的派发；在途调用仍需等待回执。暂停不代表远程执行已取消，未知结果需要核对。</p>';
    if(kind==="event")return `<label class="operation-field">事件类型<select name="kind"><option value="opinion">发起人意见</option><option value="fact">事实记录</option><option value="external_feedback">外部反馈</option></select></label>`+field("event_id","来源事件或回执 ID",crypto.randomUUID())+area("content","事件内容")+field("source","可核验来源")+`<label class="operation-field">来源标记<select name="simulated"><option value="true">模拟资料</option><option value="false">真实来源声明，仍需核验</option></select></label><p class="form-note">意见与反馈进入事件循环，不直接覆盖正式工作。</p>`;
    if(kind==="resources")return `<p class="form-note">已有 ${data.budget.calls_reserved} 次调用占用不会返还。当前上限 ${data.budget.max_calls} 次，单次 ${data.organization.resources.timeout_seconds} 秒。</p>`+field("max_calls","新的累计调用上限",data.budget.max_calls,"number",`min="${Math.max(1,data.budget.calls_reserved)}" max="10000"`)+field("timeout_seconds","新的单次超时（秒）",data.organization.resources.timeout_seconds,"number",'min="1" max="3600"')+reason();
    if(kind==="amend")return rules(data.charter)+reason();
    return `<label class="operation-field">待核对执行<select name="run_id">${data.runs.filter(r=>r.status==="unknown").map(r=>`<option value="${esc(r.id)}">${esc(r.id)} · ${esc(r.work_id || "组织决定")}</option>`).join("")}</select></label><label class="operation-field">核对结论<select name="resolution"><option value="confirmed_not_executed">有依据确认未执行</option><option value="abandon">放弃本次执行</option></select></label>`+reason()+`<p class="form-note">核对不退款，不自动重试，也不自动导入远程成果。</p>`;
  }
  function showError(message) { $("operation-error").textContent=message; $("operation-error").hidden=false; }
  function openCommand(kind) {
    if(blocked(kind))return notify(blocked(kind));
    draft={kind,orgId:kind==="create" ? null : orgId,submitted:false,request:null};
    $("operation-title").textContent=titles[kind]; $("operation-fields").innerHTML=form(kind);
    $("operation-form").hidden=false; $("operation-result").hidden=true; $("operation-error").hidden=true;
    $("operation-preview").hidden=true; $("commit-operation").hidden=true;
    $("operation-dialog").showModal();
  }
  function readForm() {
    const values=Object.fromEntries(new FormData($("operation-form")));
    const kind=draft.kind;
    if(["create","resources"].includes(kind)) {
      const resources={max_calls:Number(values.max_calls),timeout_seconds:Number(values.timeout_seconds)};
      if(kind==="resources")return {resources,reason:values.reason};
      return {name:values.name,goal:values.goal,board_name:values.board_name,resources,charter:{...JSON.parse(values.charter_rules),text:values.charter_text}};
    }
    if(kind==="amend")return {charter:{...JSON.parse(values.charter_rules),text:values.charter_text},reason:values.reason};
    if(kind==="start")return {executor:values.executor,max_steps:Number(values.max_steps),max_seconds:Number(values.max_seconds),allow_unknown_cost:values.allow_unknown_cost==="on"};
    if(kind==="event")return {...values,simulated:values.simulated==="true"};
    return values;
  }
  function preview(event) {
    event.preventDefault(); if(draft.submitted)return;
    try {
      if(blocked(draft.kind))throw new Error(blocked(draft.kind));
      if(draft.orgId && draft.orgId!==orgId)throw new Error("组织已切换，请关闭后重新选择操作");
      const value=readForm();
      if(Object.values(value).some(v=>typeof v==="string" && !v.trim()))throw new Error("必填内容不能只包含空格");
      if(draft.kind==="start" && value.executor==="codex" && !value.allow_unknown_cost)throw new Error("请明确接受本次有限调用的费用未知条件");
      draft.request={id:crypto.randomUUID(),kind:draft.kind,organization_id:draft.orgId,base_version:draft.kind==="create" ? null : data.organization.version,data:value};
      const previous=draft.kind==="resources" ? data.organization.resources : draft.kind==="amend" ? data.charter : null;
      $("operation-preview").innerHTML=`<h3>${esc(titles[draft.kind])} · 提交预览</h3><p>目标：${esc(draft.orgId || "新组织")} · 基准版本 ${draft.request.base_version ?? "新建"}</p>${previous ? `<p>当前采用</p><pre class="detail-data">${pretty(previous)}</pre><p>拟采用</p>` : ""}<pre class="detail-data">${pretty(value)}</pre>${draft.kind==="amend" ? `<p>受影响的未完成工作：${works().filter(w=>!["delivered","cancelled"].includes(w.status)).map(w=>esc(w.title)).join("、") || "无"}。撤回文本工具后相关未完成工作暂停。</p>` : ""}<small>只有服务器回执确认后，操作才生效。取消不会提交。</small>`;
      $("operation-preview").hidden=false; $("commit-operation").hidden=false; $("commit-operation").disabled=false; $("operation-error").hidden=true;
    } catch(error) { showError(errorText(error)); $("commit-operation").hidden=true; }
  }
  function showReceipt(receipt) {
    const known=confirmedReceipts.get(receipt.id);
    if(known && known.status!=="accepted")receipt=known;
    $("operation-result").hidden=false;
    $("operation-result").innerHTML=`<section class="operation-success">${badge(receipt.status)}<h3>${esc(receipt.message)}</h3><p>请求 ${esc(receipt.id)}<br>组织 ${esc(receipt.organization_id || "尚未创建")}<br>操作者 ${esc(receipt.actor)} · 基准版本 ${receipt.base_version ?? "新建"}</p><button class="button secondary" data-query-receipt="${esc(receipt.id)}">查询此请求回执</button></section>`;
    if(receipt.status==="rejected" && draft?.hasForm!==false) { draft.submitted=false; draft.request=null; $("operation-form").hidden=false; $("commit-operation").hidden=true; $("operation-preview").hidden=true; showError(receipt.message+"；输入已保留，请刷新后重新预览。"); }
    else $("operation-form").hidden=true;
  }
  async function submit() {
    if(!draft?.request || draft.submitted)return;
    if(blocked(draft.kind))return showError(blocked(draft.kind));
    if(draft.orgId && (orgId!==draft.orgId || draft.request.base_version!==data.organization.version))return showError("版本冲突或组织已切换；请重新预览，输入已保留。");
    draft.submitted=true; $("commit-operation").disabled=true;
    const request=draft.request;
    pending.push({id:request.id,organization_id:request.organization_id,kind:request.kind}); savePending();
    try {
      const result=await api("/api/commands",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(request)});
      await acceptReceipt(result.receipt);
      if(draft?.request?.id===request.id || draft?.kind===request.kind)showReceipt(result.receipt);
      await refresh();
    } catch(error) {
      const known=confirmedReceipts.get(request.id);
      if(known) { if(draft?.request?.id===request.id)showReceipt(known); return; }
      showError(errorText(error)+"；操作结果尚未确认。请查询原请求 "+request.id+"，不要重复提交。");
      $("operation-result").hidden=false;
      $("operation-result").innerHTML=`<p>结果尚未确认</p><button type="button" class="button secondary" data-query-receipt="${esc(request.id)}">查询原请求回执</button>`;
      disconnected(errorText(error));
    }
  }
  async function acceptReceipt(receipt) {
    const known=confirmedReceipts.get(receipt.id);
    if(known && known.status!=="accepted")return;
    confirmedReceipts.set(receipt.id,receipt);
    if(receipt.kind==="create" && receipt.status==="succeeded" && pending.some(p=>p.id===receipt.id) && orgId!==receipt.organization_id) { orgId=receipt.organization_id; data=null;offset=0;epoch++;lastSequence=-1; }
    if(receipt.status!=="accepted") { pending=pending.filter(p=>p.id!==receipt.id); savePending(); }
  }
  async function queryPending() {
    for(const item of [...pending]) {
      try {
        const response=await api(`/api/receipts?id=${encodeURIComponent(item.id)}${item.organization_id ? "&organization_id="+encodeURIComponent(item.organization_id) : ""}`);
        await acceptReceipt(response.receipt);
        if(draft?.request?.id===item.id && $("operation-dialog").open)showReceipt(response.receipt);
      } catch(error) { if(error.status===401)throw error; }
    }
  }

  document.addEventListener("click",event=>{
    const target=event.target.closest("[data-nav],[data-command],[data-detail],[data-clear],[data-activity],[data-page],[data-query-receipt]"); if(!target)return;
    if(target.dataset.nav) { page=target.dataset.nav; render(); }
    if(target.dataset.command)openCommand(target.dataset.command);
    if(target.dataset.detail)detail(target.dataset.detail,target.dataset.id);
    if(target.hasAttribute("data-clear")) { query="";workFilter="all";memberFilter="all";render(); }
    if(target.dataset.activity) { activityFilter=target.dataset.activity;render(); }
    if(target.dataset.page) { offset=Math.max(0,offset+Number(target.dataset.page)*50);refresh(); }
    if(target.dataset.queryReceipt) {
      const item=pending.find(p=>p.id===target.dataset.queryReceipt) || {id:target.dataset.queryReceipt,organization_id:draft?.orgId};
      if(!$("operation-dialog").open) { draft={kind:item.kind,orgId:item.organization_id,request:{id:item.id},submitted:true,hasForm:false};$("operation-title").textContent="查询操作回执";$("operation-form").hidden=true;$("operation-dialog").showModal(); }
      api(`/api/receipts?id=${encodeURIComponent(item.id)}${item.organization_id ? "&organization_id="+encodeURIComponent(item.organization_id) : ""}`).then(async r=>{await acceptReceipt(r.receipt);showReceipt(r.receipt);refresh();}).catch(e=>showError(errorText(e)));
    }
  });
  document.addEventListener("input",event=>{
    if(event.target.id==="task-search") { query=event.target.value;filterWork(); }
    if(event.target.closest("#operation-fields") && draft && !draft.submitted) { draft.request=null;$("operation-preview").hidden=true;$("commit-operation").hidden=true; }
  });
  document.addEventListener("change",event=>{
    if(event.target.id==="work-filter") { workFilter=event.target.value;filterWork(); }
    if(event.target.id==="member-filter") { memberFilter=event.target.value;filterWork(); }
    if(event.target.id==="org-select") { epoch++;orgId=event.target.value;data=null;connected=false;offset=0;lastSequence=-1;detailSerial++;$("detail-dialog").close();render();refresh(); }
  });
  $("operation-form").addEventListener("submit",preview); $("commit-operation").addEventListener("click",submit);
  for(const id of ["close-operation","cancel-operation"])$(id).addEventListener("click",()=>$("operation-dialog").close());
  $("close-dialog").addEventListener("click",()=>$("detail-dialog").close());
  $("detail-dialog").addEventListener("close",()=>detailSerial++);
  for(const id of ["detail-dialog","operation-dialog"])$(id).addEventListener("click",e=>{if(e.target===$(id)){const rect=$(id).getBoundingClientRect();if(e.clientX<rect.left || e.clientX>rect.right || e.clientY<rect.top || e.clientY>rect.bottom)$(id).close();}});
  $("refresh").addEventListener("click",refresh);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh();});
  setInterval(()=>{if(!document.hidden)refresh();},4000);
  async function initialize() {
    epoch++;serial++;if(controller)controller.abort();connected=false;latestInstance="";lastSequence=-1;
    controls();
    const ticket=new URLSearchParams(location.hash.slice(1)).get("launch");
    if(ticket) {
      history.replaceState(null,"",location.pathname);
      try { await api("/api/session",{method:"POST",headers:{"X-Union-Launch":ticket}}); }
      catch(error) { disconnected(errorText(error));return; }
    }
    await refresh();
  }
  window.addEventListener("hashchange",()=>{if(new URLSearchParams(location.hash.slice(1)).has("launch"))initialize();});
  render(); initialize();
})();
