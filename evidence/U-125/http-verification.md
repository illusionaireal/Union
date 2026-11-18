# U-125 HTTP 路由验证

2026-11-16。仅记录 U-125 的 HTTP 子工作，不关闭 U-125 或 U-111。
依据：[冻结契约](../../specs/053-union-rewrite/s01-workspace-contract.md) §2、E05。
基线为 `2b3d281f7bfb6dc3fdb8e00f432cc4f76756a8fc`，
分支 `codex/u111-v1-organization-entry`。开工时协调者文档已有修改；
本子工作的生产代码和测试原先无差异，未执行 Git 写入、在线卡写入或部署。

## 必要性与责任

旧静态入口只有平面旧路由集合，无法提供已声明的新深链接；
宽松 URL 解码也会接受不符合本契约的资产请求。文档或配置不能修正这些行为。
变更限于 [server.py](../../ai_union/server.py) 的静态路径解析和
[test_http.py](../../tests/test_http.py) 的真实 HTTP 测试。

沿原 HTTP owner 局部修改，不增加路由依赖、数据库/身份规则或数据读取。
纯路径匹配复用 `engine.ID.fullmatch`；静态文件的类型白名单、
目录约束、CSP 和同源校验保留。路径仅解码一次，先拒绝编码分隔符，
再严格检查 UTF-8、百分号残留、反斜杠、NUL 和点段。
维护复杂度在本切片范围内：一个有限模板匹配函数和原静态入口，
无第二路由服务或通用 HTML 回退。

## RED → GREEN

`TDD Route: strict`，来自用户 AGENTS。先增加行为测试，
`git diff --exit-code -- ai_union/server.py` 返回 0 后运行 RED；
失败来自真实 HTTP 状态断言，没有移除正常生产代码。

固定项目 Python，环境 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。
下面命令省略宿主 Python 的绝对路径。

| 阶段 | 命令 | 实际结果 |
| --- | --- | --- |
| RED | `python -m unittest -v tests.test_http` | 10 tests，7.594s，exit 1，42 assertion failures，无测试错误 |
| GREEN | `python -m unittest -v tests.test_http` | 10 tests，7.803s，exit 0，OK |
| 首轮相关回归 | `python -m unittest -v tests.test_http tests.test_identity_http tests.test_catalog_http tests.test_core_work_http` | 17 tests，14.820s，exit 0，OK |
| 差异检查 | `git diff --check -- ai_union/server.py tests/test_http.py` | exit 0 |

RED 的确切失败：

- `test_v1_spa_routes_serve_public_html_without_reading_au_data`：12 个请求
  返回 `404`，预期 `200`。包含全部声明模板及带旧查询参数的完整成果路径。
- `test_v1_spa_routes_preserve_public_identifier_boundaries`：21 个 AU/Work/result
  ID 位置返回 `404`，预期 `200`；覆盖 1/80 字符、内部点号和单次合法编码。
- `test_static_path_encoding_cannot_resolve_ambiguous_asset_names`：9 个请求
  返回 `200`，预期 `404`。包含编码斜杠、原始/编码点段、非法百分号、
  残留编码、无效/截断 UTF-8，并以实际存在的临时文件证明宽松解码问题。

既有认证、会话、命令/回执、旧路由与路径越界测试在 RED 阶段保持通过；
新增的同源和非法组织路径反例在基线上已通过，作为回归保留。
首轮 GREEN 后仅补充白名单资产类型、合法单次资产编码和带 `.json` 的合法 ID
回归数据，当轮无进一步生产代码变化；随后 P2 修复记录见下文。原始日志保留在宿主临时证据目录，
仓库记录不包含私有绝对路径或凭据。

## 已验证与未覆盖范围

- 新列表、组织及全部声明子路径返回准确 HTML、CSP、nosniff、DENY、
  no-referrer、no-store；将 HTTP 服务的应用引用置空仍能获取壳，
  证明这一步不读取会话、组织元数据或业务数据。
- AU/Work/result 各 ID 位置沿现行 1–80 字符语法，内部 `..`、
  类似文件扩展名的合法 ID 可用；空 ID、非法首字、超长、编码分隔符、
  点段、重复编码、非法百分号/UTF-8、额外路径拒绝为 JSON 404。
- Host、Origin、Sec-Fetch-Site 拒绝仍为 403；未知 API 在原合法会话下为
  JSON 404，未认证 API 仍保留认证边界。未声明文件路径不回退 HTML。
- 原旧地址仍只得到同一 SPA 壳；JS/CSS/SVG/WOFF2/favicon 的既有白名单可用。
  原账户登录/退出、目录错配/原创建回执、HTTP 工作链回归通过。

这是受控本机 HTTP 证据；工作链使用回环 modeld double。
页面身份/选组织、旧链接 replace、浏览器导航及四宽度、完整 Python/npm 检查、
独立工程复核由协调者完成。没有据此声明新页面已验收、真实模型、发布、
完整 V1 或持续经营通过。

## 独立评审 P2：原始请求目标的前导重复斜杠

首轮检查未覆盖标准库对前导重复斜杠的归一化。评审指出
`//organizations`、`///organizations`、`//au/a/work/w/results/r`
会返回 HTML。读取当前固定 Python 的 `BaseHTTPRequestHandler.parse_request`
确认它保留原 `requestline`，但在进入业务处理前将 `self.path` 的前导
`//` 折叠为 `/`。原静态校验仅看归一化路径，因而不能识别该违例。

在上一轮 GREEN 代码上先新增
`test_static_rejects_duplicate_leading_separators`，通过真实 HTTP 请求覆盖
根入口、组织列表（含查询参数）、旧地址、组织及成果深链接、JS 资产和 favicon。
RED 前后生产文件 SHA-256 相同；没有为了失败撤除正确实现。

| 阶段 | 命令 | 实际结果 |
| --- | --- | --- |
| P2 RED | `python -m unittest -v tests.test_http.HTTPTests.test_static_rejects_duplicate_leading_separators` | 1 test，0.771s，exit 1；10 个子断言均为 `200 != 404`，无测试错误 |
| P2 GREEN | 同上 | 1 test，0.717s，exit 0，OK |
| P2 最终相关回归 | `python -m unittest -v tests.test_http tests.test_identity_http tests.test_catalog_http tests.test_core_work_http` | 18 tests，15.750s，exit 0，OK |
| P2 差异检查 | `git diff --check -- ai_union/server.py tests/test_http.py` | exit 0 |

修复限于原 `Handler.static`：从已经成功解析的 `requestline` 取得原始请求目标，
在原路径拒绝条件中检查它是否以 `//` 开头。静态唯一调用点仍是
`handle_api`，未覆盖或替换标准库解析、API 分派、认证或授权。
正常声明地址、全部既有资产类型、CSP、同源限制及相邻 API 回归保持通过。
原始 P2 日志保留于同一宿主临时证据目录；整体浏览器及父卡验收边界保持不变。
