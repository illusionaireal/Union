# U-122 独立工程复核

2026-11-26；角色 review_u122，工作树基线 e29fb49。实施 actor 和在线成员分别记录；复核者不是产品 AU 成员。

最终未发现未解决 Critical/Important。独立执行14项成果旅程/列表测试、TypeScript检查、3项后端HTTP/SQLite用例；独立HTTP/SQLite探针验证同AU两个Work的同resultId分别返回自己的正文，缺失Work与歧义查询拒读。辅助函数探针验证中文/emoji UTF-8有效正文及AU/Work/result/seq/bytes/source/content/adoption错误、取消均拒绝。独立React/jsdom探针验证服务身份变化后正文、旧标题和来源均清除。原探针及日志留宿主。

四项Important在复核中发现并经真实RED/GREEN修正：刷新只读旧Work投影导致采用状态变化后永久409；初次正文读取返回后未核对真实会话；列表Work读取之后未核对真实会话；已知失权时正文已清除而旧标题/来源仍显示。现在刷新重读原Work，Work/正文披露前核对同principal/service/AU，失权清除受保护投影。没有延长token、放宽归属或增加另一正文事实。

现行WorkService/SQLite及Workspace仍是原所有者；新消费层不新增正文持久化、模型派发或授权。复核未代跑全量npm/Python或完整实际浏览器下载/响应式/键盘；这些由协调者取证，不能以本报告替代。本结论是工程建议，不是验收或合入授权。
