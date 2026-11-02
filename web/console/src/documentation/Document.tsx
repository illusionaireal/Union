import type { ReactNode } from 'react';

const chapters = [
  ['overview', '当前结论'], ['batches', '0–5 批次交付'], ['login', '登录与模型配置'],
  ['trial', 'NAS 试运行'], ['acceptance', '验收记录'], ['limits', '已知限制'],
  ['privacy', '部署信息边界'], ['next', '下一步开发'],
] as const;

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return <section id={id} className="doc-section"><h2>{title}<a className="heading-link" href={`#${id}`} aria-label={`链接到${title}`}>#</a></h2>{children}</section>;
}

function Code({ title, children }: { title: string; children: string }) {
  return <div className="code-block"><div className="code-title"><span>{title}</span><button type="button" className="copy-command" aria-label={`复制${title}`}>复制</button></div><pre><code>{children}</code></pre></div>;
}

const batches = [
  ['0', '基线整合', '接续 dev，修复已有回归，保留历史证据与原工作区。', '工程完成'],
  ['1', '正常登录', '管理员账号、记住设备、退出、改密及一次性恢复码。', '受控通过'],
  ['2', '模型配置体验', '目录检索、折叠高级设置、保存 / 测试 / 采用分离，AU 配置导入导出。', '受控通过'],
  ['3', '协议与接入', '四种协议、版本化目录、受限凭据引用及显式自托管端点。', '受控通过'],
  ['4', '岗位与故障回退', '按实际岗位绑定，独立备用顺序，额外请求计入额度。', '受控通过'],
  ['5', '上下文、资料与成本', '历史裁剪、图片 / PDF 输入、四类成本及期末分摊。', '受控通过'],
];

export default function Document({ revision }: { revision: string }) {
  return <html lang="zh-CN"><head>
    <meta charSet="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="UNION 正式开发与 NAS 有限试运行指南：工程交付、正常登录、模型接入、验收步骤及已知限制。" />
    <meta name="robots" content="noindex, nofollow" />
    <title>正式开发与 NAS 试运行指南 | UNION 文档</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" /><link rel="stylesheet" href="/document.css" />
    <script src="/document.js" defer />
  </head><body>
    <a className="skip-link" href="#main">跳到正文</a>
    <header className="site-header"><a className="brand" href="#overview" aria-label="UNION 文档首页"><span className="brand-mark" aria-hidden="true">U</span><strong>UNION</strong><span className="brand-divider" /><span className="brand-docs">文档</span></a><div className="header-actions"><span className="edition">更新于 2026-11-02</span><button type="button" id="print-document">打印 / PDF <span aria-hidden="true">↗</span></button></div></header>
    <div className="document-layout">
      <aside className="sidebar" aria-label="文档导航"><div className="sidebar-top"><span className="sidebar-caption">开发与交付</span><span className="stage-label">正式开发</span></div><nav aria-label="章节目录">{chapters.map(([id, name], i) => <a href={`#${id}`} key={id} data-chapter={id} aria-current={i === 0 ? 'location' : undefined}><span className="nav-index">{String(i + 1).padStart(2, '0')}</span>{name}</a>)}</nav><div className="sidebar-note"><span className="note-icon" aria-hidden="true">↳</span><p>版本事实以仓库主账及验收证据为准。此页为指定时间的文档快照。</p><a href="#sources">查看依据 <span aria-hidden="true">↗</span></a></div></aside>
      <main id="main">
        <div className="breadcrumb"><span>交付指南</span><span aria-hidden="true">/</span><span>NAS 试运行</span></div>
        <div className="page-intro"><div className="intro-label">从 MVP 进入正式开发</div><h1>正式开发与<br className="desktop-break" /> NAS 试运行指南</h1><p className="lead">把已完成的工程改造，带入真实环境。沿着登录、模型接入、组织行动与反馈的路径，验证产品能否连续使用。</p><div className="intro-meta"><span>开发主线 <code>dev</code></span><span>文档快照 <time dateTime="2026-11-02">2026-11-02</time></span></div></div>
        <Section id="overview" title="当前结论">
          <div className="callout success"><span className="callout-symbol" aria-hidden="true">↗</span><div><strong>可以安排 NAS 有限试运行</strong><p>登录与模型接入改造已进入 dev。先完成备份、构建与环境检查，再用一个真实模型、一项小任务验证完整流程。</p></div></div>
          <p>项目已进入正式开发阶段。当前结论建立在工程实现与受控验证上，真实供应商接入、NAS 本轮部署和持续运营仍需现场验收。</p>
          <dl className="evidence-strip"><div><dt>Python 回归</dt><dd>393 <span>项</span></dd><small>5 项平台跳过，其余通过</small></div><div><dt>前端测试</dt><dd>37 <span>项</span></dd><small>类型、交互与构建通过</small></div><div><dt>工作台浏览器</dt><dd>15 <span>项</span></dd><small>1440px / 320px 已检查</small></div></dl>
          <p className="caption">以上为 043 批次的工程证据，浏览器模型服务为回环替身；本批次真实供应商调用为 0。历史其他批次的真实模型记录不混算。</p>
        </Section>
        <Section id="batches" title="0–5 批次交付">
          <p>工程子项已收口。每个模块进入实际使用时，仍需验证对应账号、模型权限与目标环境。</p>
          <div className="table-scroll" role="region" aria-label="批次交付状态表，可横向滚动" tabIndex={0}><table><thead><tr><th scope="col">批次</th><th scope="col">交付内容</th><th scope="col">当前状态</th></tr></thead><tbody>{batches.map(([number, title, detail, status]) => <tr key={number}><td className="batch-number">{number}</td><td><strong>{title}</strong><p>{detail}</p></td><td><span className="status-tag">{status}</span></td></tr>)}</tbody></table></div>
          <div className="inline-note"><strong>对标验收仍在继续</strong><p>OpenClaw、Hermes、OpenCode 等接入能力的“不弱于”目标，继续按 031 逐行验收。目录数量和受控测试不能替代完整的真实接入结果。</p></div>
        </Section>
        <Section id="login" title="登录与模型配置">
          <h3>固定网址，日常账号登录</h3><p>首次通过受信宿主入口设置管理员账号，使用至少 12 字符的密码，并保存仅显示一次的恢复码。之后直接访问自己的工作台固定网址，以账号和密码登录。</p>
          <ul><li>普通登录有效 8 小时；记住设备最长 30 天。</li><li>沿用相同私有数据目录重启服务，会话继续有效。</li><li>退出会撤销当前会话；改密或恢复会撤销该账号的全部旧会话。</li></ul>
          <h3>模型配置按四个动作完成</h3><ol className="workflow"><li><strong>保存连接</strong><p>创建或选择 AU，在“模型与 API”选择协议、供应商和模型，填写实际认证信息。</p></li><li><strong>测试指定连接</strong><p>明确同意有限调用后，验证工具往返；正常路径使用两次模型请求，测试不自动切备用。</p></li><li><strong>采用连接</strong><p>显式设置组织默认模型，或为实际岗位设置模型与备用顺序。编辑连接不会自动切换默认。</p></li><li><strong>启动有限任务</strong><p>确认资源上限后，从总览启动一项小任务；保留每次尝试、用量、失败和未知回执。</p></li></ol>
          <p>配置在 AU 内独立保存，通过导出 / 导入复用。导出不含密钥或宿主凭据引用；导入不会自动测试或运行。</p>
          <details><summary>协议、订阅和费用应怎样理解？</summary><div className="details-body"><p>工程适配包括 Chat Completions、OpenAI Responses、Anthropic Messages 和 Gemini generateContent。目录收录不代表每个供应商都已真实验证。</p><p>OpenCode Go / ChatGPT 官方账号认证、最终 token 交换、实际模型权益和 AU 推理绑定分别验收。订阅认证不会自动变成普通 API 额度。</p><p>费用区分按量、订阅、自有资源和未知。估算不是实际账单；缺少依据时金额保留未知，不填 0。</p></div></details>
        </Section>
        <Section id="trial" title="NAS 试运行">
          <p>本轮采用单宿主、有限资源的试运行。以下命令由已获授权的维护者在 NAS 专用 checkout 内执行；真实连接目标从宿主私有配置读取。</p>
          <div className="trial-step"><span className="step-number">1</span><div><h3>先停止并备份</h3><p>核对是否有在途任务。按现有运维方式停止工作台及派发器，确认所有相关写入已结束，再对业务数据、配置、认证资料及当前代码版本做一致性备份。不要只复制运行中的 SQLite 主文件；WAL 和检查点须一并考虑。</p><p className="caption">数据目录、凭据和源码分别保存。发现未知外部执行时，先核对原请求，不重派。</p></div></div>
          <div className="trial-step"><span className="step-number">2</span><div><h3>更新 dev，记录实际提交</h3><p>只在干净的 dev 工作区快进更新。存在本地改动、分叉或未核对任务时停止处理，保留现场。</p><Code title="更新专用 checkout">{'set -eu\ntest "$(git branch --show-current)" = dev\nif test -n "$(git status --porcelain)"; then\n  echo "工作区有改动，请先核对并保留现场"\n  exit 1\nfi\ngit fetch origin dev\ngit merge --ff-only origin/dev\ngit rev-parse HEAD'}</Code></div></div>
          <div className="trial-step"><span className="step-number">3</span><div><h3>安装、构建并检查</h3><p>使用 Node 24.19.0 和 Python 3.11+ 的项目虚拟环境。NAS 系统 Python 可能过旧，沿用既有容器工具链；不要替换系统解释器。</p><Code title="在项目工具链环境中验证">{'npm ci --ignore-scripts\n.venv/bin/python -m pip install -r requirements-harness.lock -e .\nnpm run check\n.venv/bin/python -X utf8 -m unittest discover -v'}</Code><p className="caption">首次建立环境时，先使用满足版本要求的解释器创建 .venv。任一步失败即停止，保存日志。</p></div></div>
          <div className="trial-step"><span className="step-number">4</span><div><h3>沿用私有数据，恢复工作台</h3><p>使用现有服务入口和相同私有数据目录恢复，核对可信 HTTPS、固定网址登录与权限。先验证匿名访问被拒，再验证管理员登录和退出。初次认领仍经宿主受信入口。</p><p>既有 NAS 脚本有环境硬编码，完整配置化属于 U-054；不要直接重复执行初装脚本，也不要覆盖已有认证资料。</p></div></div>
          <div className="trial-step"><span className="step-number">5</span><div><h3>让一项小任务走完闭环</h3><p>使用已获授权的实际模型和明确调用上限，完成连接测试、任务行动、成果审读、一次反馈和后续行动。再验证暂停、重启及会话接续。</p><p>任何调用或金额授权不明确时，先停在配置验收。测试次数、费用未知和失败结果均保留。</p></div></div>
          <div className="callout warning"><span className="callout-symbol" aria-hidden="true">!</span><div><strong>Astra / Sol 外部自动开发调度器继续关闭</strong><p>既有 DSM 内核的沙箱及凭据隔离阻塞仍在。工作台和模型 API 的有限试运行单独验收，不以放开宿主权限、挂载 Docker socket 或取消沙箱方式绕过。</p></div></div>
        </Section>
        <Section id="acceptance" title="验收记录">
          <p>勾选用于记录本次核查进度，不自动建立通过结论。刷新页面会清空；可打印为 PDF 并填写实际回执。</p>
          <div className="checklist">{['已记录实际提交、工具链与备份位置（私有保存）','匿名请求被拒；固定网址登录、退出和服务重启正常','指定连接真实工具往返通过，记录连接 ID 和版本','一项真实任务产生可读成果，反馈后有后续行动','暂停和重启后的状态、调用额度与未知回执一致','失败、恢复结果、实际用量及费用未知均已记录'].map((label, i) => <label key={label}><input type="checkbox" id={`accept-${i}`} /><span>{label}</span></label>)}</div>
          <div className="acceptance-scale"><div><strong>工程完成</strong><span>代码、行为测试、独立复核</span></div><span aria-hidden="true">→</span><div><strong>真实验收</strong><span>账号、模型、任务与反馈</span></div><span aria-hidden="true">→</span><div><strong>发布与持续运行</strong><span>安装恢复、观察窗口与维护</span></div></div>
        </Section>
        <Section id="limits" title="已知限制">
          <ul className="limit-list"><li><strong>NAS 本轮部署尚未验收。</strong>这份网页只提供试运行文档，不是已更新 NAS 的证明。</li><li><strong>真实接入仍需现场完成。</strong>本批次未使用真实账号完成订阅最终登录、token 交换及 AU 推理。</li><li><strong>当前为单管理员自托管身份。</strong>公共注册、邮件找回和公共多租户账户系统不在已实现范围。</li><li><strong>成员开发工具与持续运营分别验收。</strong>宿主有 Docker 不代表 AU 成员已有开发权限；一次任务成功也不代表公司已持续经营。</li><li><strong>保守上下文估算与有限多模态。</strong>当前使用 UTF-8 字节估算，图片 / PDF 总输入上限 48KiB；不宣称精确 tokenizer 或语义压缩质量。</li></ul>
        </Section>
        <Section id="privacy" title="部署信息边界">
          <p>仓库和网页保留通用部署方法及脱敏示例。真实主机地址、SSH 用户与端口、私有部署目录及认证信息保存在宿主私有配置中，不展示在此页。</p><p>六份部署说明已经脱敏。Git 历史仍有原信息，部分宿主专用脚本仍有环境硬编码；文档脱敏不能视为历史清除或脚本配置化完成。</p><p>不要向网页文档、仓库、聊天或公共诊断输出提交密钥、口令、回调 URL、恢复码、数据库或私人日志。此文档没有模型调用、账号配置或组织管理接口。</p>
        </Section>
        <Section id="next" title="下一步开发">
          <div className="next-task"><span className="task-id">U-054</span><div><h3>准备候选版安装、升级与回滚验收包</h3><p>交付物绑定提交与依赖版本；配置、凭据、数据分离；验证旧数据兼容、失败回滚和备份恢复。把真实连接目标及私有路径移入宿主配置，保留既有安全边界。</p></div></div><p>随后继续推进真实模型接入、成员工作区和持久主机验收。组织线沿既有里程碑完成真实成立与交付，再验证持续运营。</p>
        </Section>
        <section id="sources" className="sources"><h2>文档依据</h2><p>以下为仓库内路径；本网页不公开仓库文件或私有运行证据。</p><div className="source-grid">{['docs/FORMAL_DEVELOPMENT.md','docs/MODEL_ACCESS.md','docs/DEPLOYMENT_PRIVACY.md','evidence/043-usable-model-access/matrix.md','management/project.json','TASKS.md'].map(path => <code key={path}>{path}</code>)}</div><p className="source-revision">网页源码提交 <code>{revision}</code></p></section>
        <footer><a className="footer-brand" href="#overview">UNION <span>文档</span></a><span>正式开发 / 有限试运行</span><a href="#main">回到顶部 ↑</a></footer>
      </main>
    </div><div id="copy-message" role="status" aria-live="polite" />
  </body></html>;
}
