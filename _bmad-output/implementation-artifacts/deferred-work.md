# Deferred Work

## Deferred from: code review of 1-1-项目结构初始化 (2026-04-03)

- `requirements.txt` 未锁定依赖版本 — 待全部功能实现后 `pip freeze` 固定（架构文档指定时间点）
- 密码以明文字符串存储在 credentials dict 中 — 本地工具架构设计决策；后续可引入 `SecretStr`
- `reporter.py` 骨架使用 `pass` 而非 `NotImplementedError` — Story 1.4 实现时决定是否改为抛出
- `validate.py` TODO 路径返回 0 退出码 — Story 5.1 实现完整调度逻辑时处理
- `--source` 参数未校验数据源名称合法性 — Story 5.1 实现 `choices=[...]` 或显式查找错误
- `--source` 与 `--all` 同时传入无冲突检查 — Story 5.1 处理互斥逻辑
- `reporter.py` 未包含 `reports/` 目录创建保障 — Story 1.4 实现 `write_raw_report` 时添加 `mkdir`
- `.gitignore` 中额外排除 `reports/*-raw.md` 不在 AC 规范内 — 属合理实践；下一 Story 统一确认
