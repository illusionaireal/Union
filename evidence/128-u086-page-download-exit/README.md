# evidence/128 — 父卡 #22（U-067）页面级下载出口（真实 modeld + 已采用集成）

## 结论

父卡验收的最后一段「打开或下载概览」在**已采用集成**（902b429，PR44 合并后）上以页面级真实出口补全：页面 run_loop 产出候选（digest=sha256(结果内容)、引用本次 nonce）→ 页面「下载」链接指向 `/api/v1/work/results?...` → 其响应体携带已记录结果 → 采用/交付 → 重启持久。**11/11 checks，exit 0**，单次真实派发（deepseek-v4.1-flash，用户已授权）。

## 检查清单（checks.json）

1-3. 票据页/连接/任务页（同 115/127 骨架）。
4. work registered and attempt started — 产品 API。
5. candidate result produced by the real model — 页面按钮 run_loop。
6. digest 匹配记录 sha256；7. 引用 nonce。
8. **download link present** — 候选成果卡片上的「下载」链接 href 指向 results API。
9. **downloaded content carries the recorded result** — 该 URL 响应体含记录结果。
10-11. adopt/deliver + 重启持久。

## 意义

- 父卡 #22 验收链最后一环（页面级下载）闭合：读→产→摘→采→**下**→持久全部有页面级真实证据。
- 前序：evidence/115（22-B 页面级全流程，旧基线）、127（真实中断）、本证据（已采用集成上的下载）。
