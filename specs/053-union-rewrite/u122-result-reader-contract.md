# U-122 / 在线 #75：同一组织与工作中的成果正文阅读下载

2026-11-26，基线 e29fb49。用户要求完成 #74/#75/#76；#74 已完成，#75 实时前置满足并已由 zbook-codex 认领。#76 的未完成前置及他人所有权保留，不凭本片完成自动关闭。

## 用户结果与合同

在 `/au/:auId/results` 看同组织成果；通过 `/au/:auId/work/:workId/results/:resultId` 阅读、刷新和下载同一版本正文，返回原工作。候选、已采用和该版本已交付分开显示，来源指向原步进/工具回执；采用主体和时间、交付依据沿原投影，不新增成果事实或授权。没有正文时明确空状态，读取失败可重试，不用旧页面或其他工作作为回退。

消费既有 `GET /api/v1/work` 和 `GET /api/v1/work/results?organization_id=...&work_id=...&id=...`。后者沿 WorkService.result_content 在服务器重验当前读取权和摘要，始终显式带 work_id；同 AU 相同 resultId 允许属于不同 Work。正文响应沿既有 `{protocol, organization_id, work_id, result, content}`，补全 TypeScript DTO 中已存在的采用/交付元数据字段。不更改数据库、授权、命令或调度。

前端读取以当前 Workspace 的 principal/service/AU 为边界，校验 `core.work.v1`、AU/主体和完整三元成果身份；正文对应投影的 seq/sha256/bytes/sources，实际 UTF-8 字节数和 SHA-256 再核对。失败不展示或下载正文；候选状态变化需刷新取得当前投影，不将不同时点拼为新授权。所有外部文本用 React 转义及保留换行的正文区，不执行 HTML/Markdown 脚本，也不自动加载外部内容。

下载按钮显式重新查询当前 session、当前 AU 访问、原 Work 投影和同一正文；通过全部身份、版本与摘要核对后生成 `text/plain;charset=utf-8` Blob，文件名用稳定 Work/result/seq 和 `.txt`。不直接下载 JSON，不自动 POST；object URL 及时释放。取消、卸载、切主体/AU/服务、401/403 或无效归属清除正文并取消读取/迟到下载；正文不进入 local/sessionStorage 或可跨作用域复用的查询缓存。断网显示可恢复错误，不以缓存授予下载权。

## 必要性、所有者与兼容

现有新成果路由只是缺口页；旧 ResultList 下载不带 work_id 且返回 JSON，不能满足正常阅读和相同 resultId 隔离。必须接通消费层。Workspace/路由继续原有身份与路径所有者；WorkService/SQLite 不新增责任。ResultList 收敛为使用当前已校验投影的列表；CoreResults 负责作用域读取、ResultReader 负责正文和下载。旧未挂载 Artifacts 的成果消费改绑同一实现，不维护第二列表。旧 WorkPanel/ResultDelivery 的已验证接口兼容保留，本片不挂载其手工调度/采用表单。

ArchitectureReviewRequired: no，新消费既有公开合同，不新增运行架构、schema 或授予边界。复杂度预算：两个窄界面所有者和一个正文验证辅助函数；不向 Workspace 或 WorkService 堆叠新业务逻辑，不新增缓存/正文端点/循环。正常权限与范围测试包含 producer 的真实 HTTP/SQLite 和 consumer 的实际页面。

## 实施计划与验收

TDD Route: strict，依据用户 AGENTS 明确要求。预计4–6小时，一个可观察结果，不机械拆测试/层次子卡。

1. 冻结本合同。新路由行为测试观察真实 RED：列表直达两个 Work 的同 resultId、正文而非JSON、候选/采用/交付来源、返回原工作；保留旧有效行为，调整旧 ResultList 断言以消费新合同。
2. 最小接通同一成果列表、正文 DTO/验证和下载；RED/GREEN 覆盖缺失/歧义、摘要/字节/来源错误、404/403、取消、身份/AU/服务切换、迟到响应及下载期间变化；只读零模型/命令派发。
3. 实际本地认证/HTTP/SQLite浏览器从准备好的受控成果读取、刷新、下载与返回；1440/1024/768/390/320宽、键盘焦点与长正文；同名不同Work正文隔离、篡改拒读、不执行HTML、读取无持久写入。准备成果可用明确受控fixture，不冒充 #76 的自动生成验收；真实模型调用0。
4. 固定 npm check、Python全量及受影响后端测试；另一工程角色只读复核归属/正文/下载边界，保留RED和失败历史到宿主，公开摘要索引入 evidence/U-122。
5. 仅提交本片文件、准确候选CI与普通Git集成读回；用户已关闭分支保护，不恢复保护或要求网页登录。在线完整验收后done；协调者显式保存交付镜像。继续处理 #76 前重新核对前置与交接授权。

依据：Main Chapter V1 D-03/D-04/P-04、PRD F06/F07/P15、product-design VJ04/§6、FRONTEND §3/§4.2；U-087反馈版本合同保持，不在本片新增反馈写入。
