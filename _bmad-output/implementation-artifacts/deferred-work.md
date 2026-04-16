# Deferred Work

## Deferred from: code review of 8-2-partnerboost联盟数据采集落库 (2026-04-15)

- 登录重定向校验过于宽松 — `lambda url: "login" not in url` 对错误页面也通过；与 Story 4.3 相同模式，暂缓
- `_to_float` 未处理非美元货币符号（€、括号负数等）— PartnerBoost 当前仅 USD，范围外暂缓
- `collect_date` 未做格式校验 — 调用方责任，CLI 文档已说明 YYYY-MM-DD 格式
- `sys.path.insert` 模块级副作用 — bi/ 子模块既有架构模式，统一处理
- 异常链可能泄露凭证信息 — 内部工具，受控日志环境，暂缓
- `partner` 为空字符串时复合唯一键可能碰撞 — 真实数据中不应为空，异常情况后续处理

## Deferred from: code review of 8-3-facebook-business-suite数据采集落库 (2026-04-15)

- Fallback post_id MD5 碰撞风险：同标题+日期的两条帖子 hash 相同，Doris upsert 覆盖一条 — 采集场景内容碰撞极低概率，后续可改为更强 hash 或用 URL hash
- _login() 路径 A/B 各有 time.sleep(15) 硬编码等待 — 与参考实现 social_media.py 保持一致，后续优化
- SESSION_FILE 目录创建无 mode=0o700，在多用户机器上 session 文件可被他人读取 — 生产环境单用户部署，暂不处理
- page.type() 逐键入密码，若开启 Playwright 追踪则密码明文记录 — 未启用追踪，后续可改为 page.fill()
- _try_session() 中 time.sleep(5) 硬编码，慢网络可能 session 未完全写入 — 与参考实现一致
- 正则 \d{10,} 排除短数字 ID，老帖子可能触发降级 fallback — 10位以上覆盖当前 Facebook ID 格式

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
- 无样本数量上限 MAX_SAMPLE_ROWS [sources/cartsee.py:_extract_table_records] — 项目级决策，大量行场景暂未遇到，参考 awin.py MAX_SAMPLE_ROWS=20 模式
- _try_extract_json_data 返回未经结构验证的 JS 对象 [sources/cartsee.py:_try_extract_json_data] — 辅助回退路径，主路径为 HTML table 提取；实际触发概率极低

## Deferred from: code review of 2-1-triplewhale-数据源接入 (2026-04-03)

- `resp.json()` 未处理 JSONDecodeError [sources/triplewhale.py: _fetch_table] — 防御性编码，规范未要求；API 返回非 JSON 时 traceback 可见，不静默失败
- `_get_api_key` KeyError 传播无 [triplewhale] 日志前缀 [sources/triplewhale.py: _get_api_key] — credentials 模块负责 ValueError，_get_api_key 职责明确；Epic 5 集成时统一添加错误层

## Deferred from: code review of 2-1-triplewhale-数据源接入 Correct Course (2026-04-07)

- 私有函数 _fetch_earliest_date/_fetch_row_count 未对 table_name/date_col 做 SQL 参数校验 [sources/triplewhale.py] — 私有函数仅由已校验的 fetch_data_profile 调用；date_col 来自硬编码字典，非用户输入
- HTTP 5xx 静默返回 []，_fetch_row_count 返回 0 而非 None [sources/triplewhale.py: _run_sql_query, _fetch_row_count] — 与现有 _fetch_table 5xx 降级策略一致；引入 sentinel 区分"空表"与"查询失败"留待后续
- profiles 为空时 write_triplewhale_data_profile 仍写表头 [reporter.py] — 极端边界场景；可在未来加 `if not profiles: return` 保护
- _fetch_earliest_date 重复查 _TABLE_DATE_COLUMNS [sources/triplewhale.py] — 防御性自包含设计；改签名需同步测试
- RATE_LIMIT_RPM=0 时触发 ZeroDivisionError [sources/triplewhale.py] — 常量硬编码=60，无触发路径
- COUNT 查询失败时 total_rows 显示 0 而非 "-" [reporter.py, validate.py] — 同 5xx 降级；可引入 sentinel 或 None 值在报告层显示"-"

## Deferred from: code review of 2-1-triplewhale-数据源接入 Correct Course (2026-04-04)

- `test_all_valid_tables_accepted` 路由断言为浅层（仅验证不抛 ValueError）[tests/test_triplewhale.py: TestFetchSample.test_all_valid_tables_accepted] — 超出 AC7 要求，属测试深度改进项；可在后续质量轮次中断言 call_args[0][0] == table_name
- 6 张新表 URL 路由端点不确定性（table_name 直接拼接到 BASE_URL）[sources/triplewhale.py: _fetch_table] — Dev Notes 已注明，属预先 deferred 已知问题；实际集成时需确认各表端点路径

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

## Deferred from: code review of 4-1-awin-爬虫数据源接入 (2026-04-03)

- 集成测试仅断言返回类型 (bool/list)，不验证正确性 [tests/test_awin.py] — 集成测试最低限度验证，覆盖率改进留待后续质量轮次
- fetch_sample() 入口未记录 mask 后的凭证日志 [sources/awin.py:50-57] — 日志一致性改进，非安全漏洞；后续统一日志规范时处理

## Deferred from: code review of 4-3-partnerboost-爬虫数据源接入 (2026-04-03)

- `authenticate()` debug/info 日志级别不一致 [sources/partnerboost.py:49] — 调用账号 mask 用 debug 级、认证结果用 info 级，属代码品质问题；统一日志级别可在后续质量改进轮次中处理
- 登录逻辑在 `authenticate()` / `fetch_sample()` 中重复 — 架构设计决策：两函数职责不同（验证 vs 抓取），提取公共 `_login(page)` 函数留待后续重构
- headless 模式未设 viewport，可能影响 SPA 渲染 — 可在 `p.chromium.launch()` 后调用 `browser.new_context(viewport={"width": 1280, "height": 800})`；留作可选改进

## Deferred from: code review of 3-2-youtube-数据源接入 (2026-04-03)

- AC4 缺失：`write_raw_report` 未在 source 模块中调用 [sources/youtube.py] — 架构设计决策：`validate.py`（Epic 5）dispatcher 负责协调 reporter 调用，source 模块只负责三个公开接口
- `resp.json()` 未处理 `JSONDecodeError` [sources/youtube.py:87] — 防御性编码，规范未要求；API 返回非 JSON 时 traceback 可见，不静默失败（同 triplewhale 延后模式）

## Deferred from: code review of 5-1-validate.py-cli-入口与调度器 (2026-04-03)

- `--source` 与 `--all` 同时传入时静默忽略 `--all` [validate.py:147] — AC 未明确禁止，`args.source` 优先；如需互斥可加 mutually_exclusive_group
- 硬编码 `"triplewhale"` 字符串做多表路由判断 [validate.py:78] — Story 规范明确要求此路由逻辑；如需泛化可引入 source 配置对象

## Deferred from: code review of 5-2-端到端集成验证 (2026-04-03)

- 每个测试方法重复5行 setup 代码，应提取为 fixture [tests/test_e2e.py] — 与 test_validate.py 保持一致的既有模式，可在后续测试重构时统一处理
- import 语句写在测试方法体内而非模块级 [tests/test_e2e.py] — 与 test_validate.py 既有风格一致，Python 合法写法，可在后续统一重构
- `_make_all_mock_sources` 硬编码8个 source 名称 [tests/test_e2e.py:47] — 与 test_validate.py 保持一致，新增 source 时需同步更新两处
- `--all` 测试中 social_media 使用正常 mock，未体现真实 NotImplementedError [tests/test_e2e.py:47] — 属设计决策（Dev Notes 明确），如需验证真实行为可在 AC3 相关测试中补充
- AC4 未覆盖 triplewhale 多表场景下 validation.md 保护 — 超出规格要求的额外覆盖，可在后续扩展测试时补充
- AC2/AC3 未测试 `authenticate()` 直接抛异常场景 — AC2 规格仅要求"返回 False"场景，异常场景已由 test_validate.py AC7 部分覆盖

## Deferred from: code review of 4-5-facebook-business-suite-爬虫数据源接入 (2026-04-08)

- FACEBOOK 凭证强制全局注册 [config/credentials.py] — 与其他 11 个数据源凭证注册方式一致，项目设计如此
- `sync_playwright` None 检查缺失（Playwright 未安装时 TypeError）[sources/social_media.py] — 与 awin.py/cartsee.py 等相同模式
- `PlaywrightTimeoutError = Exception` fallback 导致异常过度捕获 [sources/social_media.py] — 与 awin.py 相同模式
- CAPTCHA 检测可能对含关键词的帖子正文误报 [sources/social_media.py `_check_captcha()`] — 与 awin.py 相同 innerText 检测方案，设计限制
- 90s 总超时未覆盖 `_extract_post_rows` 内部等待 [sources/social_media.py] — 与 awin.py 两点检测设计一致
- 空样本仅 warning 不抛异常 [sources/social_media.py `fetch_sample()`] — 与 awin.py 相同
- `authenticate()` 和 `fetch_sample()` 各自独立登录，无会话复用 [sources/social_media.py] — 与 awin.py/cartsee.py 设计一致
- ARIA 分支按位置映射字段，列序错误时静默产生错误数据 [sources/social_media.py `_extract_post_rows()`] — 动态 SPA 页面结构未知，fallback 设计限制

## Deferred from: code review of 4-6-youtube-studio-爬虫数据源接入 (2026-04-08)

- Fixture 有 2 条记录但运行时 `_extract_analytics_metrics` 固定返回 1 条，nullable 相关测试覆盖的场景在生产中不会出现 [tests/test_youtube_studio.py] — 测试设计优化，不影响功能正确性
- `test_credentials.py::test_all_13_keys_present_in_result` 方法名中的 "13" 已过时（现为 16 个键）[tests/test_credentials.py] — 预存问题，方法体使用动态 `_REQUIRED_KEYS` 所以断言正确
- `_login()` post-login URL 检查仅覆盖 `accounts.google.com` 和 `signin`，不覆盖 Google 其他中间域名 [sources/youtube_studio.py:307] — 需整体 Google 登录流优化，与 social_media.py 同模式

## Deferred from: code review of 1-5-报告体系重构-聚合文档与AI分析 (2026-04-09)

- `_escape_cell` 未转义 Markdown 强调字符 (`*`, `_`, `` ` ``) [reporter.py:53] — 预存行为，Story 1-4 以来未处理；API 返回值含这些字符时报告渲染会异常
- tiktok 单表异常时 `result["success"]` 仍为 True — 部分成功未标识 [validate.py:116-117] — 预存设计，tiktok 多接口路由的容错策略，需产品决策是否区分部分成功

## Deferred from: code review of 6-1-目录初始化与公共写入工具 (2026-04-15)

- 中途批次失败无 rollback [common/doris_writer.py:65-69] — spec 设计如此，每批单独 commit；Doris 非完整 ACID，rollback 对已提交批次无效
- doris_config.py 明文密码 + root 用户 [doris_config.py:11] — 项目级设计，spec 明确"一字不差"复制既有模式
- table/column 名直接拼入 SQL [common/doris_writer.py:50-58] — 内部工具，调用方完全可控
- SET enable_insert_strict=false 压制部分 DB 错误 [common/doris_writer.py:64] — spec 必要配置，Doris upsert 要求
- 全部列均为 unique_key 时退化为普通 INSERT 无告警 [common/doris_writer.py:47-59] — spec 未要求此告警
- total_written 统计提交行数而非 rowcount [common/doris_writer.py:70] — spec 设计如此
- DorisConfig 单例非线程安全 [doris_config.py:3-13] — 项目级既定模式
- logger.error + re-raise 重复日志 [common/doris_writer.py:75-76] — 可接受，有助排查
- DB_CONFIG 未指定 charset [doris_config.py:7-13] — 复制自既有模式，需统一评估

## Deferred from: code review of 6-2-水位线管理器 (2026-04-15)

- sys.path.insert 模块级 hack [watermark.py:11] — 与 doris_writer.py 一致的既有项目模式
- datetime.utcnow() Python 3.12 已废弃 [watermark.py:82] — 当前 3.11.2，项目统一模式，升级 Python 时处理
- SELECT * 脆弱于 schema 变更 [watermark.py:63] — 内部 5 列表，pre-existing 模式
- source/table 参数无长度校验 VARCHAR(64/128) [watermark.py:57,112] — 内部工具，doris_writer.py 同样无校验
- success_time 无时区信息 [watermark.py:79-82] — 项目统一使用 naive UTC
- last_success_time 从 pymysql 返回类型不保证 datetime [watermark.py:65] — 驱动版本依赖，项目级问题
- 并发写入 update_watermark 无原子性 [watermark.py:73-89] — 调度器单实例场景，pre-existing
- except Exception 捕获过宽 [watermark.py:45,68,100,118] — 与 doris_writer.py 一致的既有模式

## Deferred from: code review of 7-3-钉钉多维表数据采集落库 (2026-04-16)

- `KeyError` on missing env vars (collectors/dingtalk_collector.py): by design fail-fast; key name appears in error; consider explicit message in future
- `datetime.utcnow()` deprecated: Python 3.11 still works; address when upgrading Python version
- empty `record_id=""` when DingTalk recordId absent (sdk/dingtalk/client.py): DingTalk API contract guarantees recordId; theoretical only
- `_is_ms_timestamp` matches large negative numbers (collectors/dingtalk_collector.py): DingTalk timestamps are not negative; theoretical boundary
- `write_to_doris` key-consistency failure on sparse API responses (common/doris_writer.py): DingTalk bitable schema is fixed per sheet
- `_flatten_value` + `linkedRecordIds` implicit contract (sdk/dingtalk/client.py): currently correct; add explicit guard or comment in future
- `sys.path.insert` at module level (collectors/dingtalk_collector.py): project-wide pattern; pre-existing
