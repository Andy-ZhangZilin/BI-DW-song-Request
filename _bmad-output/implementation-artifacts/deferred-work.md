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

## Deferred from: code review of 4-2-cartsee-爬虫数据源接入 (2026-04-03)

- URL 含 "login" 子路径时登录成功判断可能误判 [sources/cartsee.py:authenticate()] — CartSee 实际 URL 结构未知，推测性问题，集成测试时验证
- fetch_sample() 无整体 60s 超时限制 [sources/cartsee.py:fetch_sample()] — 各步骤均有 15s timeout，暂不加全局 timer；若将来出现超时问题再补充
- pytest.ini 未配置 addopts 默认过滤 integration 测试 [pytest.ini] — 设计选择，手动 -m "not integration" 符合项目约定

## Deferred from: code review of 2-1-triplewhale-数据源接入 (2026-04-03)

- `resp.json()` 未处理 JSONDecodeError [sources/triplewhale.py: _fetch_table] — 防御性编码，规范未要求；API 返回非 JSON 时 traceback 可见，不静默失败
- `_get_api_key` KeyError 传播无 [triplewhale] 日志前缀 [sources/triplewhale.py: _get_api_key] — credentials 模块负责 ValueError，_get_api_key 职责明确；Epic 5 集成时统一添加错误层

## Deferred from: code review of 2-2-tiktok-shop-数据源接入 (2026-04-03)

- 模块级全局变量 `_access_token`/`_shop_cipher` 非线程安全 [sources/tiktok.py:26-27] — 架构层设计决策，单线程 CLI 场景不影响正确性
- `nullable` 推断仅基于 `sample[0]` 第一条记录 [sources/tiktok.py:256] — page_size=1 场景 by design，字段发现用途可接受
- `access_token` 过期无感知，`fetch_sample` 无自动重认证 [sources/tiktok.py:181] — 字段发现工具 authenticate+fetch_sample 连续调用设计，可在 Epic 5 集成层添加重试
- `_sign_request` 未主动过滤 `sign` 键（调用顺序防护）[sources/tiktok.py:34] — 现有调用点均在 sign 前签名，潜在地雷而非当前 bug
- 无 HTTP 重试/退避逻辑 [sources/tiktok.py] — 超出本 Story 范围，可在 Epic 5 集成层统一处理
- 嵌套对象/数组字段 `sample_value` 在报告中 `str()` 化后冗长 [sources/tiktok.py:260] — reporter._escape_cell 系统性行为，非 tiktok 独有

## Deferred from: code review of 4-4-社媒后台-stub-模块 (2026-04-03)

- 测试仅验证 stub 行为，未来实现替换时测试需同步更新 [tests/test_social_media.py] — stub 被替换为真实实现时，pytest 测试将自然失效并需要更新，属预期工作
- `extract_fields`/`fetch_sample` 未覆盖非空/非标准输入参数的测试 [tests/test_social_media.py] — stub 中全部输入行为相同；非标准输入边界测试在真实实现时补充

## Deferred from: code review of 3-2-youtube-数据源接入 (2026-04-03)

- AC4 缺失：`write_raw_report` 未在 source 模块中调用 [sources/youtube.py] — 架构设计决策：`validate.py`（Epic 5）dispatcher 负责协调 reporter 调用，source 模块只负责三个公开接口
- `resp.json()` 未处理 `JSONDecodeError` [sources/youtube.py:87] — 防御性编码，规范未要求；API 返回非 JSON 时 traceback 可见，不静默失败（同 triplewhale 延后模式）
