# Story 5.1: validate.py CLI 入口与调度器

Status: done

## Story

作为操作者，
我希望通过 `python validate.py --source <名称>` 或 `python validate.py --all` 一条命令运行验证，
以便我能获得带明确执行状态的控制台反馈，并在单源失败时不影响其他数据源继续运行。

## Acceptance Criteria

1. 运行 `python validate.py --source triplewhale` 时，仅运行 triplewhale 的 authenticate → fetch_sample → extract_fields → write_raw_report 流程，控制台输出每个步骤结构化日志，格式为 `[triplewhale] {操作描述} ... 成功/失败`
2. 运行 `python validate.py --all` 时，按顺序运行全部已实现数据源（triplewhale / tiktok / dingtalk / youtube / awin / cartsee / partnerboost），每个数据源独立执行，任一数据源失败不中断其他数据源
3. 某个数据源执行中抛出异常时，调度器 try/except 捕获，日志输出完整错误信息（含错误类型和来源），该数据源标记为失败，其余数据源正常继续执行
4. 所有数据源执行完毕后，全部成功则退出码为 `0`；有任一数据源失败则退出码为 `1`；控制台输出汇总结果（各数据源：成功/失败）
5. 运行 `python validate.py --help` 时，显示 `--source` 和 `--all` 参数说明及示例命令
6. `get_credentials()` 在启动阶段校验失败（缺少必填凭证键）时，立即打印缺失凭证列表并以非零退出码退出，不进入调度循环（快速失败）
7. social_media 数据源（stub 模块）被 `--all` 调用时抛出 `NotImplementedError`，调度器捕获该异常，标记该数据源为失败，继续执行后续数据源

## Tasks / Subtasks

- [x] 实现 validate.py 调度核心逻辑 (AC: #1 #2 #3 #4 #6 #7)
  - [x] 在 main() 中初始化 logging（basicConfig，level=INFO，格式含时间戳）
  - [x] 定义 SOURCES 注册表（OrderedDict 或普通 dict，按固定顺序：triplewhale/tiktok/dingtalk/youtube/awin/cartsee/partnerboost/social_media）
  - [x] 在调度前调用 `get_credentials()`，捕获 `ValueError` 后打印缺失列表并 `sys.exit(1)`（快速失败）
  - [x] 实现 `_run_source(source_name, source_module, creds)` 私有函数：authenticate → fetch_sample → extract_fields → write_raw_report → init_validation_report，每步输出结构化日志
  - [x] 对 triplewhale 进行 4 表迭代（TABLES = pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf），每张表独立调用 fetch_sample + extract_fields + write_raw_report
  - [x] 实现调度循环：`for source_name, module in sources_to_run.items(): try/except Exception as e`，捕获所有异常，记录失败信息，继续执行
  - [x] 实现 `authenticate()` 返回 False 时：记录为认证失败，跳过 fetch_sample，标记该源失败
  - [x] 执行完毕后打印汇总表格（各数据源：成功/失败/原因）并根据是否有失败决定退出码
- [x] 完善 argparse 帮助文本 (AC: #5)
  - [x] 为 `--source` 添加 `metavar` 和 `choices`（或 help 中说明可选数据源列表）
  - [x] 为 `--all` 完善 help 文本，说明运行顺序
  - [x] 在 `epilog` 中添加示例命令
- [x] 创建 tests/test_validate.py 单元测试 (AC: #1 #2 #3 #4 #6 #7)
  - [x] mock 所有 source 模块和 reporter 函数
  - [x] 测试 `--source triplewhale`：仅 triplewhale 被调用，退出码 0
  - [x] 测试 `--all` 全部成功：所有 source 被调用，退出码 0
  - [x] 测试单源 authenticate 返回 False：该源标记失败，其余继续，退出码 1
  - [x] 测试单源 fetch_sample 抛出异常：该源标记失败，其余继续，退出码 1
  - [x] 测试 `--all` 中 social_media 抛出 NotImplementedError：被捕获，其余继续，退出码 1
  - [x] 测试 get_credentials() 抛出 ValueError：直接 sys.exit(1)，不进入调度循环
  - [x] 验证 `pytest tests/ -m "not integration"` 全部通过（19/19 新增测试通过，1 个预存失败与本 Story 无关）

## Dev Notes

### 核心实现要求

**当前 validate.py 现状（须在此基础上实现，不需重写框架）：**

```python
# 当前骨架（已有）
def main() -> None:
    parser = argparse.ArgumentParser(
        description="outdoor-data-validator: 验证各数据源 API 接入与字段发现"
    )
    parser.add_argument("--source", type=str, help="指定单个数据源名称（如 triplewhale）")
    parser.add_argument("--all", action="store_true", help="运行全部数据源的验证")
    args = parser.parse_args()

    if not args.source and not args.all:
        parser.print_help()
        sys.exit(1)

    # TODO: Story 5.1 实现调度逻辑
```

**完整实现结构（参考，不必一字不差）：**

```python
"""outdoor-data-validator — 统一 CLI 验证入口"""
import argparse
import logging
import sys
from typing import Any

import reporter
from config.credentials import get_credentials
from sources import triplewhale, tiktok, dingtalk, youtube, awin, cartsee, partnerboost, social_media

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 数据源注册表（有序，按推荐运行顺序）
# social_media 是 stub，--all 时也纳入（调度器统一捕获 NotImplementedError）
SOURCES: dict[str, Any] = {
    "triplewhale": triplewhale,
    "tiktok": tiktok,
    "dingtalk": dingtalk,
    "youtube": youtube,
    "awin": awin,
    "cartsee": cartsee,
    "partnerboost": partnerboost,
    "social_media": social_media,
}

# triplewhale 4 张表的固定路由列表（与 triplewhale.py 中 TABLES 常量一致）
TRIPLEWHALE_TABLES: list[str] = [
    "pixel_orders_table",
    "pixel_joined_tvf",
    "sessions_table",
    "product_analytics_tvf",
]
```

**单源运行逻辑（_run_source 私有函数）：**

```python
def _run_source(source_name: str, module: Any) -> bool:
    """执行单个数据源的完整验证流程，返回是否成功。"""
    logger.info(f"[{source_name}] 开始验证 ...")
    try:
        ok = module.authenticate()
        if not ok:
            logger.error(f"[{source_name}] 认证 ... 失败")
            return False
        logger.info(f"[{source_name}] 认证 ... 成功")

        if source_name == "triplewhale":
            # triplewhale 多表路由：每张表独立跑一遍
            for table_name in TRIPLEWHALE_TABLES:
                logger.info(f"[{source_name}] 获取 {table_name} 样本 ...")
                sample = module.fetch_sample(table_name)
                fields = module.extract_fields(sample)
                reporter.write_raw_report(source_name, fields, table_name, len(sample))
                reporter.init_validation_report(source_name)
                logger.info(f"[{source_name}] {table_name} 报告 ... 成功")
        else:
            sample = module.fetch_sample()
            fields = module.extract_fields(sample)
            reporter.write_raw_report(source_name, fields, None, len(sample))
            reporter.init_validation_report(source_name)

        logger.info(f"[{source_name}] 验证完成 ... 成功")
        return True

    except Exception as e:
        logger.error(f"[{source_name}] 执行失败：{type(e).__name__}: {e}")
        return False
```

**调度主循环（main() 中的调度部分）：**

```python
# 快速失败：凭证校验
try:
    get_credentials()
except ValueError as e:
    logger.error(f"凭证校验失败：{e}")
    sys.exit(1)

# 确定要运行的数据源列表
if args.source:
    if args.source not in SOURCES:
        logger.error(f"未知数据源：{args.source}，可用数据源：{list(SOURCES.keys())}")
        sys.exit(1)
    sources_to_run = {args.source: SOURCES[args.source]}
else:  # --all
    sources_to_run = SOURCES

# 执行调度循环
results: dict[str, str] = {}
for source_name, module in sources_to_run.items():
    success = _run_source(source_name, module)
    results[source_name] = "成功" if success else "失败"

# 汇总输出
logger.info("=" * 50)
logger.info("验证汇总：")
for name, status in results.items():
    logger.info(f"  {name}: {status}")
logger.info("=" * 50)

failed = [name for name, status in results.items() if status != "成功"]
sys.exit(0 if not failed else 1)
```

### 关键实现约束

**1. triplewhale 多表处理**

- triplewhale 必须循环跑 4 张表，每张表独立生成 raw 报告（raw.md 每次覆盖）
- triplewhale.py 中的 `TABLES` 常量为 `["pixel_orders_table", "pixel_joined_tvf", "sessions_table", "product_analytics_tvf"]`
- raw 报告文件名仍为 `triplewhale-raw.md`（reporter 按 source_name 命名），但会被 4 次覆盖，最终保留最后一张表的内容——这是现有设计，不需要改 reporter
- **如需保留 4 张表报告**：可在 _run_source 中对 triplewhale 用 f"{source_name}_{table_name}" 作为 source_name 传给 reporter——但 epics 中 AC 未要求，保持最简实现即可

**2. social_media 在 --all 中的行为**

AC 7 明确：social_media 抛出 NotImplementedError 时，调度器捕获异常，标记为失败，继续执行。
`_run_source` 用 `except Exception as e` 已覆盖 `NotImplementedError`，无需额外处理。

**3. 凭证快速失败**

`get_credentials()` 在 `config/credentials.py` 中定义，缺少凭证时抛出 `ValueError`。
validate.py 在进入调度循环前调用一次，捕获 ValueError 并立即 sys.exit(1)。

**4. 日志格式统一**

```python
# 操作日志格式（架构规范）
logger.info(f"[{source_name}] 认证 ... 成功")
logger.error(f"[{source_name}] 认证 ... 失败：{error_detail}")
```

logging.basicConfig 在模块级初始化，format 包含时间戳。

**5. validate.py 保持单一职责**

`validate.py` 只做 CLI 解析 + 调度，不包含任何报告渲染逻辑（reporter.py 负责）、凭证加载逻辑（credentials.py 负责）。

### 测试实现要点

**测试文件：`tests/test_validate.py`**

由于 validate.py 用 `main()` 包裹逻辑，测试时使用 `sys.argv` mock + `pytest.raises(SystemExit)` 验证退出码。

**推荐测试结构：**

```python
import pytest
from unittest.mock import patch, MagicMock
import sys

# 注意：所有 source 模块需在 import validate 之前 patch，否则 SOURCES 注册表已固化
# 推荐用 importlib 或在 fixture 中 patch validate.SOURCES

def make_mock_source(auth_result=True, sample=None, fields=None):
    """工厂函数：返回一个预设行为的 mock source 模块"""
    m = MagicMock()
    m.authenticate.return_value = auth_result
    m.fetch_sample.return_value = sample or [{"field": "value"}]
    m.extract_fields.return_value = fields or [{"field_name": "f", "data_type": "string", "sample_value": "v", "nullable": False}]
    return m
```

**关键 mock 路径：**
- `validate.SOURCES`：patch 整个 SOURCES 字典，替换为 mock source
- `validate.get_credentials`（或 `config.credentials.get_credentials`）：控制凭证校验
- `validate.reporter`（或 `reporter.write_raw_report`、`reporter.init_validation_report`）：防止实际写文件

**测试用例映射：**

| AC | 测试用例 |
|----|---------|
| AC1 | `--source triplewhale`：仅 triplewhale mock 被调用，其他 source mock 未调用，退出码 0 |
| AC2 | `--all`：所有 source mock 被调用 |
| AC3 | 某 source fetch_sample 抛 RuntimeError：该源标记失败，其余继续 |
| AC4 | 全部成功 → exit 0；任一失败 → exit 1 |
| AC5 | `--help`：argparse 输出含 --source 和 --all（通过 parser.format_help() 验证） |
| AC6 | get_credentials 抛 ValueError → sys.exit(1)，不调用任何 source |
| AC7 | social_media.authenticate 抛 NotImplementedError → 被捕获，标记失败，后续 source 继续 |

**triplewhale 在 --source 模式下的测试：**
需验证 `fetch_sample` 被调用 4 次（对应 4 张表），每次传入不同的 table_name。

### 既有代码参照

**reporter.py 公开接口（已完整实现）：**
- `write_raw_report(source_name, fields, table_name, sample_count)` → 写 `reports/{source}-raw.md`
- `init_validation_report(source_name)` → 首次创建 `reports/{source}-validation.md`，已存在则跳过

**credentials.py 快速失败接口：**
```python
# config/credentials.py
def get_credentials() -> dict[str, str]:
    # 缺少凭证时 raise ValueError(f"缺少以下必需凭证：{', '.join(missing)}")
```

**各 source 模块已有公开接口（统一契约）：**
```python
def authenticate() -> bool
def fetch_sample(table_name: str = None) -> list[dict]
def extract_fields(sample: list[dict]) -> list[dict]
```

**triplewhale.py TABLES 常量（可直接引用）：**
```python
from sources.triplewhale import TABLES as TRIPLEWHALE_TABLES  # 或在 validate.py 中硬编码
# ["pixel_orders_table", "pixel_joined_tvf", "sessions_table", "product_analytics_tvf"]
```

### 不需修改的文件

以下文件在本 Story 中**不应修改**：
- `reporter.py`（已完整实现）
- `config/credentials.py`（已完整实现）
- `sources/*.py`（所有 source 模块已完整实现）
- `tests/conftest.py`（已有 mock_credentials fixture）

### Project Structure Notes

**新增 / 修改文件：**
- `validate.py`：在骨架基础上实现完整调度逻辑（修改）
- `tests/test_validate.py`：新增单元测试

**不修改的文件：**
- `reporter.py`、`config/credentials.py`、`sources/*.py`、`tests/conftest.py`

**目录规范：**
- 测试文件命名：`tests/test_validate.py`（与 source 命名规范一致）
- 无需新增 fixtures/（reporter 和 source 均 mock）

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1: validate.py CLI 入口与调度器]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns] — 错误处理规范调度器代码示例
- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns] — 日志格式规范
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries] — 内部数据流
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns] — 统一 source 接口
- [Source: validate.py] — 当前骨架（argparse、--source、--all 已有）
- [Source: reporter.py] — write_raw_report / init_validation_report 已完整实现
- [Source: config/credentials.py] — get_credentials() / mask_credential() 已完整实现
- [Source: sources/triplewhale.py#TABLES] — 4 张表的路由常量

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

测试初版 2 个用例失败（`test_help_contains_source_and_all`、`test_credentials_failure_exits_with_code_1`），
根因：测试体内误用 `importlib.reload(validate)` 而非 `validate.main()`。修正后 19/19 全通过。

### Completion Notes List

- 实现 `validate.py` 完整调度逻辑：SOURCES 注册表（8 个数据源）、logging.basicConfig、_run_source() 私有函数、main() 调度主循环
- triplewhale 多表特殊处理：导入 TRIPLEWHALE_TABLES 常量，每张表独立调用 fetch_sample + extract_fields + write_raw_report
- 快速失败：get_credentials() 抛 ValueError 时立即 sys.exit(1)，不进入调度循环
- 失败隔离：调度循环每个 source 独立 try/except，NotImplementedError 和所有 Exception 均被捕获
- 汇总输出：所有 source 完成后打印 = 分隔汇总，全部成功退出码 0，任一失败退出码 1
- argparse 完善：--source 增加 metavar 和可选值说明，--all 说明执行顺序，epilog 含示例命令
- 新增 tests/test_validate.py：19 个测试用例，覆盖全部 7 条 AC，含 _run_source() 细粒度测试
- 回归：263/264 非集成测试通过，1 个预存失败（triplewhale.py 注释含 os.getenv 字符串被 test_credentials.py 误检），与本 Story 无关

### File List

- validate.py（修改 — 实现完整调度逻辑）
- tests/test_validate.py（新增 — 19 个单元测试）

### Review Findings

- [x] [Review][Patch] triplewhale 循环内重复调用 `init_validation_report` [validate.py:85] — 已移至循环外部，仅调用一次
- [x] [Review][Defer] `--source` 与 `--all` 同时传入时静默忽略 `--all` [validate.py:147] — deferred, pre-existing
- [x] [Review][Defer] 硬编码 `"triplewhale"` 字符串做路由判断 [validate.py:78] — deferred, pre-existing
