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

## Deferred from: code review of 1-2-凭证管理器 (2026-04-03)

- short credential 前4位全部暴露 [config/credentials.py:75] — 设计决策：实际凭证长度 32+，影响可忽略
- load_dotenv 在模块导入时执行 [config/credentials.py:13] — Story 1.1 遗留行为，conftest 已通过 patch 缓解
- 纯空白字符串凭证未被 `if not value` 拦截 [config/credentials.py:46] — Story 1.1 遗留行为，不在本 Story 范围内修复
- mask_credential 尚未在任何生产日志路径调用 [config/credentials.py:57] — 将由 source Stories 2.x–4.x 落实
- mask_credential(None) 抛出 TypeError [config/credentials.py:57] — 调用方契约，类型注解已明确声明 str

## Deferred from: code review of 1-3-字段需求配置 (2026-04-03)

- `display_name` 唯一性未在测试中验证 — 当前 story 未要求，可在 reporter.py 消费阶段（Story 1-4）渲染时处理重复展示问题
- `source` 字段未验证为已存在的模块名 — sources/ 目录由 Story 1-1 创建，此时无法验证；在 Story 2-x 接入数据源时补充集成测试
- SQL 数据源 `table` 字段未验证为非空字符串 — 数据完整性校验属 reporter.py 运行时职责，届时可在加载后统一校验
- 未覆盖省略 `table` 键（vs 显式 `table: null`）的测试用例 — 两种写法在 PyYAML 中语义等价（均返回 None），当前 story 范围内低优先级

## Deferred from: code review of 1-4-报告渲染器 (2026-04-03)

- `_load_field_requirements` 每次调用重新读取 YAML 无缓存 [reporter.py:33] — 性能优化，非正确性问题；此工具运行频率低，不阻塞当前功能
- `write_text` 无 IO 异常处理（权限/磁盘错误）[reporter.py:171] — 防御性改进，调用方会收到明确的 traceback；可在 Epic 5 集成时统一添加错误处理层
