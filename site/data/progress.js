window.UNION_DATA = {
  "schema_version": 1,
  "iteration": "001-org-bootstrap",
  "source": "local fixture validation snapshot",
  "validated_at": "2026-10-11T04:14:10.608948+08:00",
  "base_commit": "24845e3eb3709645356aa835564c67ed60b628bb",
  "metrics": {
    "tests_passed": 25,
    "members": 2,
    "artifacts": 3,
    "real_model_calls": 0,
    "fixture_calls": 6
  },
  "verification": {
    "mechanism_scenario_passed": true,
    "real_agent_verified": false,
    "external_delivery_verified": false,
    "external_market_feedback_verified": false,
    "wheel_installed_in_isolation": true
  },
  "limitations": [
    "本页面是验证快照，不是实时组织后台",
    "演示是 fixture 重放，不调用模型或修改数据库",
    "真实 Agent 协作尚未试跑",
    "真实发布与市场反馈尚未接入"
  ],
  "capabilities": [
    [
      "F01 · 目标与章程",
      "组织身份、目标、章程采用与资源持久化",
      "当前仅本地测试采用"
    ],
    [
      "F02 · 临时启动",
      "启动权限一次性提交，至少两成员任职",
      "模型自组织尚未运行"
    ],
    [
      "F03 · 正式决定",
      "身份、权限、版本、引用与事务校验",
      "真实执行器输出待实测"
    ],
    [
      "F04 · 成员协作",
      "Codex CLI 适配与跨成员依赖接口",
      "当前执行来自 fixture"
    ],
    [
      "F05 · 成果保存",
      "文件、版本、SHA-256 与任务来源",
      "当前为模拟文本成果"
    ],
    [
      "F06 · 后续行动",
      "成果进入组织决定并派发后续工作",
      "真实模型判断待验证"
    ],
    [
      "F07 · 责任交接",
      "任职调整、未完成责任与旧权限撤回",
      "受控机制测试通过"
    ],
    [
      "F08 · 等待与恢复",
      "持久复查、事件唤醒、未知执行核对",
      "无长期运行可靠性结论"
    ],
    [
      "F09 · 章程修订",
      "受信董事会入口、历史与新授权生效",
      "本地身份信任边界"
    ],
    [
      "F10 · 资料与上下文",
      "岗位、任务、依赖与版本清单",
      "仅支持文本资料"
    ],
    [
      "F11 · 状态观察",
      "CLI 状态、事件、决定与用量",
      "网站展示验证快照"
    ],
    [
      "F12 · 有限资源",
      "调用占用、超时和 token 回执记录",
      "Codex 金额费用未知"
    ]
  ],
  "artifacts": [
    {
      "name": "source.md",
      "work_id": "work-one",
      "version": 1,
      "sha256": "8e30a61dafefb0b55ff3393227ca2206b14a62c5bd9d84ff9808d0924b005d08",
      "content": "# 模拟资料\n此文件用于验证任务来源和跨成员上下文；没有模型、市场研究或外部发布。",
      "path": "data/source.md"
    },
    {
      "name": "dependent.md",
      "work_id": "work-two",
      "version": 1,
      "sha256": "b9e215dda840dcc09ae273eca401a2f471d9a17c7f97d55d8bed094730cefec0",
      "content": "# 模拟依赖成果\n依据 work-one/source.md 的模拟资料形成。下一步验证组织决定能派发后续动作。",
      "path": "data/dependent.md"
    },
    {
      "name": "followup.md",
      "work_id": "work-followup",
      "version": 1,
      "sha256": "76b5ba85ec9c9574d8899cfd57bc0b1d7c27e13a53706c0210dbd170ff4d6eb5",
      "content": "# 模拟后续动作\n前一轮模拟资料触发了组织决定与此工作。没有对外发布或真实反馈。",
      "path": "data/followup.md"
    }
  ],
  "steps": [
    {
      "title": "从一句目标开始",
      "label": "目标",
      "description": "原始目标、章程与有限资源已保存。此刻还没有成员或工作。",
      "phase": "待启动",
      "version": 0,
      "calls": 0,
      "members": false,
      "work": [],
      "event": "目标与测试章程已准备"
    },
    {
      "title": "组织安排成为正式状态",
      "label": "组织",
      "description": "通用启动决定建立两名测试成员、岗位与任职，并派发存在依赖的工作。有效提交后，临时启动授权结束。",
      "phase": "组织已形成",
      "version": 1,
      "calls": 1,
      "members": true,
      "work": [
        "pending",
        "dependent"
      ],
      "event": "启动决定提交；临时启动授权结束"
    },
    {
      "title": "成员 A 保存第一份成果",
      "label": "首次行动",
      "description": "测试成员 A 执行 work-one，实际测试程序保存 source.md，并登记任务来源与文件校验摘要。",
      "phase": "协作进行中",
      "version": 3,
      "calls": 2,
      "members": true,
      "work": [
        "done",
        "pending"
      ],
      "event": "work-one 交付；source.md 已保存"
    },
    {
      "title": "成员 B 使用依赖资料",
      "label": "依赖协作",
      "description": "成员 B 的工作包包含成员 A 的成果和资料版本。work-two 交付 dependent.md，跨成员依赖得到机制验证。",
      "phase": "首次协作完成",
      "version": 5,
      "calls": 3,
      "members": true,
      "work": [
        "done",
        "done"
      ],
      "event": "work-two 交付；跨成员资料依赖可追踪"
    },
    {
      "title": "成果触发下一轮决定",
      "label": "后续决定",
      "description": "决策责任岗位引用已交付工作，创建 work-followup。决定、状态变更和待办在同一事务中保存。",
      "phase": "后续工作已派发",
      "version": 6,
      "calls": 4,
      "members": true,
      "work": [
        "done",
        "done",
        "pending"
      ],
      "event": "依据 work-one / work-two 创建后续任务"
    },
    {
      "title": "后续决定落实为行动",
      "label": "后续行动",
      "description": "成员 B 实际执行测试程序中的后续工作，保存 followup.md。闭环包含行动与可读取文件，不止一份计划。",
      "phase": "后续工作完成",
      "version": 8,
      "calls": 5,
      "members": true,
      "work": [
        "done",
        "done",
        "done"
      ],
      "event": "work-followup 交付；第 3 份成果已保存"
    },
    {
      "title": "等待新事件，保留状态",
      "label": "持久等待",
      "description": "最后的决定登记等待；没有新事件时不再调用执行器。新进程读取已有成员、工作和成果，保持等待。",
      "phase": "等待新事件",
      "version": 9,
      "calls": 6,
      "members": true,
      "work": [
        "done",
        "done",
        "done"
      ],
      "event": "持久等待；重启后没有新增调用"
    }
  ],
  "work": [
    {
      "id": "work-one",
      "title": "生成模拟资料",
      "member": "A",
      "dependency": "无依赖"
    },
    {
      "id": "work-two",
      "title": "使用依赖成果",
      "member": "B",
      "dependency": "依赖 work-one"
    },
    {
      "id": "work-followup",
      "title": "完成后续动作",
      "member": "B",
      "dependency": "依赖 work-two"
    }
  ]
};
