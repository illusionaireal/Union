"use strict";

(() => {
  const data = window.UNION_DATA;
  if (!data) return;
  const $ = (id) => document.getElementById(id);
  const make = (tag, className, value) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  };
  const metrics = data.metrics;
  const textDownload = (content, mime = "text/plain") => "data:" + mime + ";charset=utf-8," + encodeURIComponent(content);
  $("report-download").href = textDownload(JSON.stringify(data, null, 2) + "\n", "application/json");
  $("test-count").textContent = metrics.tests_passed;
  $("member-count").textContent = metrics.members;
  $("artifact-count").textContent = metrics.artifacts;
  $("real-count").textContent = metrics.real_model_calls;
  const date = new Date(data.validated_at);
  $("snapshot-date").textContent = "验证记录：" + new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
  data.capabilities.forEach((row) => {
    const tr = make("tr");
    row.forEach((cell) => tr.append(make("td", "", cell)));
    $("capability-table").append(tr);
  });

  let current = 0;
  let timer = null;
  const timeline = [];
  data.steps.forEach((step, index) => {
    const li = make("li");
    const button = make("button", "timeline-button");
    button.type = "button";
    button.setAttribute("aria-label", "查看阶段 " + index + "：" + step.title);
    button.append(make("span", "timeline-circle", String(index).padStart(2, "0")), make("span", "", step.label));
    button.addEventListener("click", () => { stop(); current = index; render(); });
    li.append(button);
    $("demo-timeline").append(li);
    timeline.push({ li, button });
  });

  function stop() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    $("play-symbol").textContent = "▶";
    $("play-label").textContent = current === data.steps.length - 1 ? "重播演示" : "播放演示";
    $("demo-play").setAttribute("aria-label", $("play-label").textContent);
  }

  function render() {
    const step = data.steps[current];
    timeline.forEach(({ li, button }, index) => {
      li.className = index === current ? "active" : index < current ? "done" : "";
      if (index === current) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
    $("demo-step-number").textContent = String(current).padStart(2, "0");
    $("demo-step-title").textContent = step.title;
    $("demo-step-description").textContent = step.description;
    $("demo-stage-tag").textContent = step.phase;
    $("inspector-phase").textContent = step.phase;
    $("inspector-version").textContent = "v" + step.version;
    $("inspector-calls").textContent = step.calls;
    $("budget-fill").className = "budget-" + step.calls;
    const artifactCount = step.work.filter((state) => state === "done").length;
    $("inspector-artifacts").textContent = artifactCount + " 份";
    $("demo-prev").disabled = current === 0;
    $("demo-next").disabled = current === data.steps.length - 1;
    if (timer === null) stop();
    const members = $("demo-members");
    members.replaceChildren();
    if (!step.members) {
      members.append(make("div", "empty-members", "启动决定提交后，成员与任职才成为正式状态。"));
    } else {
      ["A", "B"].forEach((name) => {
        const card = make("div", "demo-member");
        const details = make("div");
        details.append(make("strong", "", "测试成员 " + name), make("small", "", name === "A" ? "Fixture One · 测试责任一" : "Fixture Two · 测试责任二"));
        const state = current === 6 ? "等待" : current >= (name === "A" ? 2 : 3) ? "已执行" : "已任职";
        card.append(make("span", "avatar " + (name === "A" ? "violet" : "mint"), name), details, make("span", "member-state", state));
        members.append(card);
      });
    }
    const work = $("demo-work");
    work.replaceChildren();
    if (step.work.length === 0) work.append(make("div", "work-empty", "尚未派发工作"));
    const statuses = { done: "已交付", pending: "待执行", dependent: "等待依赖" };
    step.work.forEach((state, index) => {
      const task = data.work[index];
      const row = make("div", "work-row" + (state === "done" ? " completed" : ""));
      const left = make("div");
      const copy = make("div");
      copy.append(make("strong", "", task.title + " · 成员 " + task.member), make("small", "", task.id + " / " + task.dependency));
      left.append(make("span", "work-icon", state === "done" ? "✓" : "▤"), copy);
      row.append(left, make("span", "tag " + (state === "done" ? "verified" : "neutral"), statuses[state]));
      work.append(row);
    });
    const events = $("demo-events");
    events.replaceChildren();
    data.steps.slice(Math.max(0, current - 2), current + 1).reverse().forEach((item) => {
      const li = make("li", "", item.event);
      li.append(make("time", "", "状态 v" + item.version + " / 模拟调用 " + item.calls));
      events.append(li);
    });
  }

  $("demo-play").addEventListener("click", () => {
    if (timer !== null) { stop(); return; }
    if (current === data.steps.length - 1) current = 0;
    timer = window.setInterval(() => {
      current += 1;
      if (current >= data.steps.length - 1) { current = data.steps.length - 1; stop(); }
      render();
    }, 1400);
    render();
    $("play-symbol").textContent = "Ⅱ";
    $("play-label").textContent = "暂停演示";
    $("demo-play").setAttribute("aria-label", "暂停演示");
  });
  $("demo-next").addEventListener("click", () => { stop(); current = Math.min(current + 1, data.steps.length - 1); render(); });
  $("demo-prev").addEventListener("click", () => { stop(); current = Math.max(current - 1, 0); render(); });
  $("demo-reset").addEventListener("click", () => { stop(); current = 0; render(); });
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
  render();

  const architecture = {
    governance: { category: "GOVERNANCE", title: "授权与章程", description: "组织的运行边界是版本化的数据，由受信董事会入口采用或修订。每次新行动检查当前生效规则。", responsibilities: ["记录章程版本、采用身份与修订依据", "普通成员不能通过填写身份冒充董事会", "修章传播到新行动与受影响的在途工作"], boundary: "章程不会自动提供外部账号、工具或资金；组织不能修改宿主权限或运行内核。", source: "engine.py · create / amend / _authorize" },
    runtime: { category: "ORGANIZATION RUNTIME", title: "组织循环", description: "收集成果与事件，按内部规则找到决策责任岗位。Agent 提出结构化操作，程序校验后提交并派发。", responsibilities: ["绑定实际成员身份与任职依据", "校验权限、对象引用和基础状态版本", "事务保存决定、正式状态与待办"], boundary: "不固定 CEO 或内容生产岗位。无任务、无事件时等待；未知执行结果进入核对流程。", source: "engine.py · apply_decision\nrunner.py · step / run / watch" },
    executor: { category: "EXECUTOR ADAPTER", title: "成员执行器", description: "稳定的成员身份与模型会话分离。统一工作包交给现有 Codex CLI，接回状态、结构化成果与可用 token 回执。", responsibilities: ["提供 submit、status 与 result 接口", "约束工具范围、调用数与单次超时", "fixture 与真实 Codex 路径明确区分"], boundary: "适配器接口已测试，真实 Codex 仍未调用。不保证远程取消、会话恢复或恰好执行一次。", source: "executor.py · CodexExecutor / FixtureExecutor\nprotocol.py · 工作与决定协议" },
    context: { category: "CONTEXT & MEMORY", title: "上下文与记忆", description: "根据岗位、任职和任务关系组装必要信息。依赖成果及其版本随工作包传递，换会话后仍能继续履职。", responsibilities: ["读取目标、当前章程与内部规则", "包含任务依赖、组织记忆和相关文本成果", "保存使用的资料与上下文版本清单"], boundary: "首轮支持文本资料与组织记忆；没有向量库、知识图谱或任意资料访问工具。", source: "engine.py · _context / context\nprotocol.py · instructions" },
    state: { category: "STATE & EVENTS", title: "持久化状态", description: "SQLite 保存组织快照、章程、事件、决定、执行和资源记录。正式状态串行提交，数据与活跃进程分别处理。", responsibilities: ["事务提交与过期决定冲突检查", "重复回执去重、调用额度占用持久化", "保存复查时间和待办，重启后核对未知执行"], boundary: "当前为单组织、单应用本地原型。进程、远程连接与认证状态不能视为随快照存活。", source: "engine.py · transaction / recover / wake_due" },
    artifacts: { category: "ARTIFACTS & EVIDENCE", title: "版本化成果", description: "成果属于组织或任务，保留版本、执行来源和文件校验摘要。实际文件存在且可读取，才支持完成声明。", responsibilities: ["保存本地文本文件及 SHA-256 摘要", "关联任务、执行、成员与授权版本", "保留旧版本，并由独立评测核验成果"], boundary: "首轮仅支持文本资产。可打开文件不等于已真实发布，也不等于获得市场反馈。", source: "engine.py · finish_work / _read_artifact\nevaluation.py · evaluate" },
  };
  const nodes = document.querySelectorAll("[data-node]");
  function showArchitecture(key) {
    const info = architecture[key];
    nodes.forEach((node) => { const selected = node.dataset.node === key; node.classList.toggle("selected", selected); node.setAttribute("aria-pressed", String(selected)); });
    $("architecture-category").textContent = info.category;
    $("architecture-name").textContent = info.title;
    $("architecture-description").textContent = info.description;
    $("architecture-boundary").textContent = info.boundary;
    $("architecture-source").textContent = info.source;
    $("architecture-responsibilities").replaceChildren(...info.responsibilities.map((value) => make("li", "", value)));
  }
  nodes.forEach((node) => node.addEventListener("click", () => showArchitecture(node.dataset.node)));
  showArchitecture("runtime");

  const dialog = $("artifact-dialog");
  let artifactIndex = 0;
  function showArtifact(index) {
    artifactIndex = index;
    const artifact = data.artifacts[index];
    $("artifact-content").textContent = artifact.content;
    $("artifact-work").textContent = artifact.work_id + " / " + artifact.name;
    $("artifact-version").textContent = "版本 v" + artifact.version;
    $("artifact-download").href = textDownload(artifact.content);
    $("artifact-download").setAttribute("download", artifact.name);
    document.querySelectorAll(".artifact-tab").forEach((tab, i) => { tab.classList.toggle("selected", i === index); tab.setAttribute("aria-pressed", String(i === index)); });
  }
  data.artifacts.forEach((artifact, index) => {
    const button = make("button", "artifact-tab", artifact.name);
    button.type = "button";
    button.addEventListener("click", () => showArtifact(index));
    $("artifact-tabs").append(button);
  });
  $("view-artifacts").addEventListener("click", () => { stop(); showArtifact(artifactIndex); dialog.showModal(); });
  $("close-artifacts").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { const box = dialog.getBoundingClientRect(); if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close(); });
})();
