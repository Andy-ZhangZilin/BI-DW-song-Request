# Deferred Work

## Deferred from: code review of 8-3-facebook-business-suite数据采集落库 (2026-04-15)

- Fallback post_id MD5 碰撞风险：同标题+日期的两条帖子 hash 相同，Doris upsert 覆盖一条 — 采集场景内容碰撞极低概率，后续可改为更强 hash 或用 URL hash
- _login() 路径 A/B 各有 time.sleep(15) 硬编码等待 — 与参考实现 social_media.py 保持一致，后续优化
- SESSION_FILE 目录创建无 mode=0o700，在多用户机器上 session 文件可被他人读取 — 生产环境单用户部署，暂不处理
- page.type() 逐键入密码，若开启 Playwright 追踪则密码明文记录 — 未启用追踪，后续可改为 page.fill()
- _try_session() 中 time.sleep(5) 硬编码，慢网络可能 session 未完全写入 — 与参考实现一致
- 正则 \d{10,} 排除短数字 ID，老帖子可能触发降级 fallback — 10位以上覆盖当前 Facebook ID 格式
