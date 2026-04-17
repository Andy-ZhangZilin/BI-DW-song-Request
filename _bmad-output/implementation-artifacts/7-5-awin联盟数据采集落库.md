# Story 7.5：Awin 联盟数据采集落库

Status: done

## Story

作为数据工程师，
我希望能将 Awin 联盟交易数据采集并写入 Doris，
以便构建联盟营销渠道的佣金和转化报表。

## Acceptance Criteria

1. **Given** `AWIN_API_TOKEN` 和 `AWIN_ADVERTISER_ID` 环境变量已配置；**When** 运行 `awin_collector.py`；**Then** 通过 Awin Transactions API 拉取交易记录（含分页），upsert 写入 `hqware.ods_awin_transactions`，以 `transaction_id` 为唯一主键

2. **Given** 首次运行（水位线为 None）；**When** `get_watermark("awin", "transactions")` 返回 `None`；**Then** 全量拉取（start_date 使用 `AWIN_EARLIEST_DATE`，默认 `2024-01-01`）

3. **Given** 非首次运行；**When** `get_watermark` 返回历史记录；**Then** 增量拉取：`start_date = last_success_time - lookback_days`（默认 30 天回溯），`end_date = 今天`；回溯窗口通过 `AWIN_LOOKBACK_DAYS` 环境变量配置

4. **Given** API 返回空列表；**When** 当前时间段内无交易；**Then** 记录 info 日志跳过写入，正常更新水位线（end_date 更新为今天）

5. **Given** 写入 Doris 成功；**When** 查看日志；**Then** 输出 `[awin_collector][hqware.ods_awin_transactions] 写入 N 行 ... 成功`

6. **Given** API Token 无效（401/403）；**When** 调用认证；**Then** 抛出 `RuntimeError("[awin_collector] API Token 无效")`，不静默失败

7. **Given** 使用 `--mode full` 参数运行；**When** `reset_watermark` 被调用；**Then** 水位线重置，下次触发全量拉取

8. **Given** 单元测试环境；**When** 运行 `tests/test_awin_collector.py`；**Then** 所有单元测试通过（mock requests + mock doris_writer + mock watermark）

## Tasks / Subtasks

- [x] Task 1：实现 `collectors/awin_collector.py` (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Task 1.1：定义常量和环境变量读取（`AWIN_API_TOKEN`、`AWIN_ADVERTISER_ID`、`AWIN_LOOKBACK_DAYS`、`AWIN_EARLIEST_DATE`）
  - [x] Task 1.2：实现 `_fetch_transactions(token, advertiser_id, start_date, end_date)` → 支持分页，返回 `list[dict]`
  - [x] Task 1.3：实现 `_transform(raw_records)` → 字段映射，返回 Doris 格式 `list[dict]`
  - [x] Task 1.4：实现 `collect(mode: str = "incremental")` 主入口函数（全量/增量判断 + 水位线读写）
  - [x] Task 1.5：实现 `if __name__ == "__main__"` 入口（`--mode full|incremental`，`--lookback-days`，`--start-date`，`--end-date`）

- [x] Task 2：编写单元测试 `tests/test_awin_collector.py` (AC: 8)
  - [x] Task 2.1：测试 `_transform()` 字段映射和类型转换
  - [x] Task 2.2：测试 `collect()` 首次运行（watermark=None → 全量）
  - [x] Task 2.3：测试 `collect()` 增量运行（watermark 有记录 → 回溯 30 天）
  - [x] Task 2.4：测试 `collect()` API 返回空列表（正常退出，更新水位线）
  - [x] Task 2.5：测试 `collect()` API Token 无效（RuntimeError 抛出）

- [x] Task 3：更新 `sprint-status.yaml`
  - [x] Task 3.1：`epic-7` → `in-progress`，`7-5-awin联盟数据采集落库` → `review`（dev 完成后 code-review 流程改为 done）

## Dev Notes

### 文件结构

```
bi/python_sdk/outdoor_collector/
└── collectors/
    └── awin_collector.py          ← 本 Story 核心新建文件

outdoor-data-validator/
└── tests/
    └── test_awin_collector.py     ← 单元测试（主仓库 tests/ 目录）
```

> `collectors/` 在 `bi/` submodule 内；测试文件在主仓库 `tests/`。
> `bi/` submodule 修改需单独在 `bi/` 内 commit，再在主仓库更新 submodule 引用（见下方 git 操作说明）。

### Awin API 规范（继承自 Story 4.7）

**认证方式：** Bearer Token

```http
Authorization: Bearer <AWIN_API_TOKEN>
```

**交易记录端点：**

```
GET https://api.awin.com/advertisers/{advertiserId}/transactions/
```

**关键参数：**

| 参数 | 说明 | 格式 |
|------|------|------|
| `startDate` | 开始日期（含） | `YYYY-MM-DD` |
| `endDate` | 结束日期（含） | `YYYY-MM-DD` |
| `timezone` | 时区 | `UTC`（固定） |
| `dateType` | 日期类型 | `transaction`（默认） |
| `page` | 分页页码（从 1 开始） | int |
| `pageSize` | 每页记录数（最大 1000） | int，默认 1000 |

**响应结构：**

```json
[
  {
    "id": 12345678,
    "advertiserId": 89509,
    "publisherId": 123,
    "publisherName": "Publisher XYZ",
    "commissionStatus": "approved",
    "commissionAmount": {"amount": "5.00", "currency": "USD"},
    "saleAmount": {"amount": "50.00", "currency": "USD"},
    "clickRef": "ref123",
    "transactionDate": "2026-04-01T10:00:00",
    "validationDate": "2026-04-08T10:00:00",
    "type": "sale",
    "commissionGroupId": 1,
    "commissionGroupName": "Default Group"
  }
]
```

**注意事项：**
- API 返回列表（`list`），非分页对象。实际 API 可能支持 `page` 参数但返回结构可能直接是数组
- 若响应为空列表 `[]`，视为当前窗口无新数据，属正常情况
- `commissionAmount` 和 `saleAmount` 是嵌套对象，提取 `.amount` 字段
- `advertiserId: 89509`（Piscifun），从环境变量 `AWIN_ADVERTISER_ID` 读取

### 完整实现规范

**模块位置：** `bi/python_sdk/outdoor_collector/collectors/awin_collector.py`

**Import 路径处理（与 partnerboost_collector.py 保持一致）：**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common.doris_writer import write_to_doris
from common.watermark import get_watermark, update_watermark, reset_watermark
```

**常量与环境变量：**

```python
SOURCE = "awin_collector"
TABLE  = "hqware.ods_awin_transactions"
UNIQUE_KEYS = ["transaction_id"]

AWIN_API_BASE = "https://api.awin.com"
HTTP_TIMEOUT = 30          # 请求超时 30s
PAGE_SIZE    = 1000        # 每页最大记录数

# 从环境变量读取（bi/ 模块直接用 os.environ，不 import config.credentials）
def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("AWIN_API_TOKEN", "")
    advertiser_id = os.environ.get("AWIN_ADVERTISER_ID", "")
    if not token or not advertiser_id:
        raise RuntimeError(
            f"[{SOURCE}] 未配置 AWIN_API_TOKEN / AWIN_ADVERTISER_ID 环境变量"
        )
    return token, advertiser_id

LOOKBACK_DAYS = int(os.environ.get("AWIN_LOOKBACK_DAYS", "30"))
EARLIEST_DATE = os.environ.get("AWIN_EARLIEST_DATE", "2024-01-01")
```

**`_fetch_transactions()` 规范（支持分页）：**

```python
def _fetch_transactions(
    token: str,
    advertiser_id: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """调用 Awin Transactions API，支持分页，返回全部交易记录。

    Args:
        token: Bearer Token
        advertiser_id: Awin 广告主 ID
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        原始交易记录列表

    Raises:
        RuntimeError: API 请求失败（含 401/403/5xx）
    """
    url = f"{AWIN_API_BASE}/advertisers/{advertiser_id}/transactions/"
    headers = {"Authorization": f"Bearer {token}"}
    all_records: list[dict] = []
    page = 1

    while True:
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "timezone": "UTC",
            "dateType": "transaction",
            "page": page,
            "pageSize": PAGE_SIZE,
        }
        resp = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)

        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError(f"[{SOURCE}] API Token 无效（HTTP {resp.status_code}）")

        if resp.status_code != 200:
            raise RuntimeError(
                f"[{SOURCE}] API 请求失败：HTTP {resp.status_code} — {resp.text[:200]}"
            )

        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"[{SOURCE}] API 返回非列表格式：{type(data)}")

        if not data:
            break  # 无更多数据

        all_records.extend(data)

        if len(data) < PAGE_SIZE:
            break  # 最后一页
        page += 1

    logger.info(f"[{SOURCE}] 共拉取 {len(all_records)} 条交易记录（{start_date} ~ {end_date}）")
    return all_records
```

**`_transform()` 字段映射规范：**

```python
def _transform(raw_records: list[dict]) -> list[dict]:
    """将 Awin API 原始记录映射为 Doris 列格式。

    字段映射：
        id                        → transaction_id  (int)
        publisherId               → publisher_id    (int)
        publisherName             → publisher_name  (str)
        commissionStatus          → commission_status (str)
        commissionAmount.amount   → commission_amount (float)
        saleAmount.amount         → sale_amount      (float)
        clickRef                  → click_ref        (str)
        transactionDate           → transaction_date (str, ISO format)
        validationDate            → validation_date  (str or None)
        type                      → transaction_type (str)
        commissionGroupId         → commission_group_id (int)
        commissionGroupName       → commission_group_name (str)
    """
    result: list[dict] = []
    for rec in raw_records:
        comm_amount = rec.get("commissionAmount") or {}
        sale_amount = rec.get("saleAmount") or {}

        result.append({
            "transaction_id":        rec.get("id"),
            "publisher_id":          rec.get("publisherId"),
            "publisher_name":        rec.get("publisherName", ""),
            "commission_status":     rec.get("commissionStatus", ""),
            "commission_amount":     _to_float(comm_amount.get("amount")),
            "sale_amount":           _to_float(sale_amount.get("amount")),
            "click_ref":             rec.get("clickRef", ""),
            "transaction_date":      rec.get("transactionDate", ""),
            "validation_date":       rec.get("validationDate"),
            "transaction_type":      rec.get("type", ""),
            "commission_group_id":   rec.get("commissionGroupId"),
            "commission_group_name": rec.get("commissionGroupName", ""),
        })
    return result
```

**`_to_float()` 辅助函数：**

```python
def _to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None
```

**`collect()` 主入口完整规范：**

```python
def collect(mode: str = "incremental", lookback_days: int = None,
            start_date: str = None, end_date: str = None) -> int:
    """主入口：读水位线 → 确定日期范围 → 拉取交易 → 转换 → upsert 写入 Doris → 更新水位线。

    Args:
        mode: "incremental"（默认）或 "full"（忽略水位线，全量拉取）
        lookback_days: 回溯天数，默认读 AWIN_LOOKBACK_DAYS 环境变量（默认 30）
        start_date: 手动指定开始日期 YYYY-MM-DD（仅 full 模式或调试用）
        end_date: 手动指定结束日期 YYYY-MM-DD（默认今天）

    Returns:
        写入行数（0 表示无数据，正常退出）
    """
    if lookback_days is None:
        lookback_days = LOOKBACK_DAYS

    token, advertiser_id = _get_credentials()

    if mode == "full":
        reset_watermark(SOURCE, "transactions")

    if end_date is None:
        end_date = str(date.today())

    wm = get_watermark(SOURCE, "transactions")

    if wm is None or mode == "full":
        # 全量：从 EARLIEST_DATE 拉起
        effective_start = start_date or EARLIEST_DATE
        logger.info(f"[{SOURCE}] 全量模式，start_date={effective_start}, end_date={end_date}")
    else:
        # 增量：水位线回溯 lookback_days
        wm_time: datetime = wm["last_success_time"]
        if hasattr(wm_time, "date"):
            wm_date = wm_time.date()
        else:
            wm_date = datetime.fromisoformat(str(wm_time)).date()
        effective_start = str(wm_date - timedelta(days=lookback_days))
        logger.info(
            f"[{SOURCE}] 增量模式，水位线={wm_date}，回溯 {lookback_days} 天，"
            f"start_date={effective_start}, end_date={end_date}"
        )

    raw_records = _fetch_transactions(token, advertiser_id, effective_start, end_date)

    if not raw_records:
        logger.info(f"[{SOURCE}] 当前窗口无交易记录，跳过写入，更新水位线")
        update_watermark(SOURCE, "transactions", datetime.utcnow())
        return 0

    records = _transform(raw_records)
    written = write_to_doris(TABLE, records, UNIQUE_KEYS, source=SOURCE)
    update_watermark(SOURCE, "transactions", datetime.utcnow())
    return written
```

**`__main__` 入口：**

```python
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Awin 联盟数据采集落库")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    parser.add_argument("--lookback-days", type=int, default=None, help="回溯天数，默认 AWIN_LOOKBACK_DAYS 或 30")
    parser.add_argument("--start-date", default=None, help="手动开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="结束日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()
    written = collect(
        mode=args.mode,
        lookback_days=args.lookback_days,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"[{SOURCE}] 写入 {written} 行")
```

### Doris 表结构（DDL 参考，由 DBA 建表，collector 不负责 DDL）

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_awin_transactions (
    transaction_id       BIGINT       NOT NULL COMMENT 'Awin 交易 ID（主键）',
    publisher_id         INT          COMMENT '发布商 ID',
    publisher_name       VARCHAR(512) COMMENT '发布商名称',
    commission_status    VARCHAR(32)  COMMENT '佣金状态：pending/approved/declined/bonus',
    commission_amount    DECIMAL(18,4) COMMENT '佣金金额（USD）',
    sale_amount          DECIMAL(18,4) COMMENT '销售额（USD）',
    click_ref            VARCHAR(256) COMMENT '点击引用标识',
    transaction_date     DATETIME     COMMENT '交易时间（UTC）',
    validation_date      DATETIME     COMMENT '确认时间（UTC），pending 时为 NULL',
    transaction_type     VARCHAR(64)  COMMENT '交易类型（sale/lead 等）',
    commission_group_id  INT          COMMENT '佣金组 ID',
    commission_group_name VARCHAR(256) COMMENT '佣金组名称',
    updated_at           DATETIME DEFAULT NOW() COMMENT '入库时间'
)
UNIQUE KEY(transaction_id)
DISTRIBUTED BY HASH(transaction_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

### 凭证加载方式

`bi/` 内不使用 `config.credentials`（主仓库模块），直接读取环境变量：

```python
token = os.environ.get("AWIN_API_TOKEN", "")
advertiser_id = os.environ.get("AWIN_ADVERTISER_ID", "")
```

> 运行前需 `source .env` 或由海豚调度器注入环境变量。
> `.env` 中对应键名为 `AWIN_API_TOKEN`、`AWIN_ADVERTISER_ID`（已在 Story 4.7 中添加到 `.env.example`）。

### 单元测试规范 `tests/test_awin_collector.py`

**sys.path 设置（继承 test_partnerboost_collector.py 模式）：**

```python
import sys, os
sys.path.insert(0, "bi/python_sdk/outdoor_collector")
sys.path.insert(0, "bi/python_sdk/outdoor_collector/collectors")

from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime, timedelta, date

import awin_collector as ac
```

**必须覆盖的测试场景：**

```python
# 场景 1：_transform() 字段映射正确
def test_transform_basic():
    raw = [{
        "id": 12345678,
        "publisherId": 123,
        "publisherName": "Pub XYZ",
        "commissionStatus": "approved",
        "commissionAmount": {"amount": "5.00", "currency": "USD"},
        "saleAmount": {"amount": "50.00", "currency": "USD"},
        "clickRef": "ref1",
        "transactionDate": "2026-04-01T10:00:00",
        "validationDate": "2026-04-08T10:00:00",
        "type": "sale",
        "commissionGroupId": 1,
        "commissionGroupName": "Default",
    }]
    result = ac._transform(raw)
    assert len(result) == 1
    r = result[0]
    assert r["transaction_id"] == 12345678
    assert r["commission_status"] == "approved"
    assert abs(r["commission_amount"] - 5.0) < 0.001
    assert abs(r["sale_amount"] - 50.0) < 0.001

# 场景 2：collect() 首次运行 → 全量
@patch("awin_collector.get_watermark", return_value=None)
@patch("awin_collector.update_watermark")
@patch("awin_collector.write_to_doris", return_value=5)
@patch("awin_collector._fetch_transactions", return_value=[...])
def test_collect_first_run(mock_fetch, mock_write, mock_update_wm, mock_get_wm):
    with patch.dict(os.environ, {"AWIN_API_TOKEN": "tok", "AWIN_ADVERTISER_ID": "89509"}):
        written = ac.collect()
    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args
    assert call_args[0][2] == ac.EARLIEST_DATE  # start_date = EARLIEST_DATE

# 场景 3：collect() 增量运行 → 回溯 30 天
@patch("awin_collector.get_watermark")
@patch("awin_collector.update_watermark")
@patch("awin_collector.write_to_doris", return_value=2)
@patch("awin_collector._fetch_transactions", return_value=[...])
def test_collect_incremental(mock_fetch, mock_write, mock_update_wm, mock_get_wm):
    wm_date = date(2026, 4, 1)
    mock_get_wm.return_value = {"last_success_time": datetime(2026, 4, 1)}
    with patch.dict(os.environ, {"AWIN_API_TOKEN": "tok", "AWIN_ADVERTISER_ID": "89509"}):
        ac.collect(lookback_days=30)
    call_args = mock_fetch.call_args
    expected_start = str(wm_date - timedelta(days=30))
    assert call_args[0][2] == expected_start

# 场景 4：API 返回空列表 → 更新水位线，写入 0 行
@patch("awin_collector.get_watermark", return_value=None)
@patch("awin_collector.update_watermark")
@patch("awin_collector._fetch_transactions", return_value=[])
def test_collect_no_data(mock_fetch, mock_update_wm, mock_get_wm):
    with patch.dict(os.environ, {"AWIN_API_TOKEN": "tok", "AWIN_ADVERTISER_ID": "89509"}):
        written = ac.collect()
    assert written == 0
    mock_update_wm.assert_called_once()  # 水位线仍更新

# 场景 5：API Token 无效 → RuntimeError
@patch("awin_collector.get_watermark", return_value=None)
@patch("awin_collector._fetch_transactions",
       side_effect=RuntimeError("[awin_collector] API Token 无效（HTTP 401）"))
def test_collect_invalid_token(mock_fetch, mock_get_wm):
    with patch.dict(os.environ, {"AWIN_API_TOKEN": "bad", "AWIN_ADVERTISER_ID": "89509"}):
        with pytest.raises(RuntimeError, match="API Token 无效"):
            ac.collect()
```

### 防回归约束

- **不修改** `sources/awin.py`（Phase 1 成果，接口契约 authenticate/fetch_sample/extract_fields 保持不变）
- **不修改** `common/doris_writer.py`（Story 6.1 成果）
- **不修改** `common/watermark.py`（Story 6.2 成果）
- **不修改** `sdk/` 下任何文件（Story 6.0 成果，Awin 无 SDK 层，直接用 requests）
- 主仓库 `tests/` 中已有的全部测试继续通过（awin collector 新增测试文件，不影响已有测试）

### git submodule 操作说明

本 Story 修改 `bi/` 内文件，需两步 commit（从 BACKEND_ROOT_ABS 执行）：

```bash
# 步骤 A：在 bi/ 内 commit（必须先于主仓库 commit）
cd bi
git add python_sdk/outdoor_collector/collectors/awin_collector.py
git commit --author="jiuyueshang <845126847@qq.com>" \
  -m "feat(outdoor_collector): Story 7.5 — Awin 联盟数据采集落库"

# 步骤 B：在主仓库 commit（含 bi submodule 引用 + 测试文件 + story 文件 + sprint-status）
cd ..
git add bi \
    tests/test_awin_collector.py \
    _bmad-output/implementation-artifacts/7-5-awin联盟数据采集落库.md \
    _bmad-output/implementation-artifacts/sprint-status.yaml
git commit --author="jiuyueshang <845126847@qq.com>" \
  -m "feat(story-7.5): Awin 联盟数据采集落库 — done"
```

> **注意**：`tests/test_awin_collector.py` 属于主仓库，与 submodule 引用更新一起放在主仓库 commit 中。

### 关键易错点（AI Agent 必读）

1. **无 Awin SDK 层**：Story 6.0 只创建了 tiktok/triplewhale/dingtalk SDK，**Awin 无 SDK 层**，collector 直接使用 `requests` 调用 API（同 `sources/awin.py` Phase 1 方案）

2. **回溯窗口逻辑**：增量时 `start_date = watermark_date - lookback_days`，而不是直接用 `watermark_date`。这是 Awin 佣金状态延迟确认的必要设计（pending → approved 可能延迟数天）

3. **分页处理**：`_fetch_transactions` 必须循环拉取直到返回空列表或返回行数 < PAGE_SIZE

4. **嵌套字段提取**：`commissionAmount` 和 `saleAmount` 是对象，需提取 `.amount` 子字段

5. **空数据正常更新水位线**：即使 `raw_records` 为空，也要调用 `update_watermark`（将 `end_date` 时间戳写入），避免下次全量重跑

6. **`--mode full` 时先 reset**：在拉取数据前先调用 `reset_watermark`，然后调 `get_watermark`（此时返回 None），走全量逻辑

7. **凭证不 import config.credentials**：`bi/` 模块使用 `os.environ.get()`，不引用主工具的 `config.credentials`

8. **日志格式**：`[awin_collector][hqware.ods_awin_transactions] 写入 N 行 ... 成功`（由 doris_writer 自动输出）

### 与 project-context.md 的关键约束

- `bi/` 代码与主工具无依赖：不 import `validate`、`reporter`、`sources.*`、`config.credentials`
- `DorisConfig` 单例由 `doris_writer.py` 内部使用，collector 不直接实例化
- 命名规范：`snake_case`，函数类型注解必须
- `sys.path.insert` 路径处理与现有 collector 保持一致

### References

- [Source: epics.md#Story 7.5] — AC 定义、增量策略、upsert 主键
- [Source: implementation-artifacts/4-7-awin-api-migration.md] — Awin API 端点、认证方式、advertiserId、可用字段
- [Source: sources/awin.py] — Phase 1 实现参考（Bearer Token 认证、HTTP_TIMEOUT、requests 用法）
- [Source: implementation-artifacts/8-2-partnerboost联盟数据采集落库.md] — collector 整体结构参考
- [Source: implementation-artifacts/6-2-水位线管理器.md] — watermark API 规范（get/update/reset）
- [Source: implementation-artifacts/6-1-目录初始化与公共写入工具.md] — write_to_doris() 签名
- [Source: project-context.md#bi/ 子模块代码规范] — DorisConfig、凭证、git submodule 流程

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

### File List

- `bi/python_sdk/outdoor_collector/collectors/awin_collector.py`
- `tests/test_awin_collector.py`

### Review Findings

- [x] [Review][Decision] F1: 写入 0 行时是否应更新水位线 — dismissed（A）：`written=0` 属 Doris upsert 全重复的正常情况，水位线照常前进
- [x] [Review][Patch] F2: 分页循环无最大页数上限 — fixed: 新增 `MAX_PAGES=200` 常量及循环上限 guard [`awin_collector.py:47`]
- [x] [Review][Patch] F3: `transaction_id` 可为 None — fixed: `_transform()` 跳过 `id=None` 记录并记录 warning [`awin_collector.py:202-204`]
- [x] [Review][Patch] F4: `resp.json()` 未捕获 `JSONDecodeError` — fixed: 捕获 `ValueError` 并包装为 `RuntimeError` [`awin_collector.py:141-143`]
- [x] [Review][Patch] F5: `_get_lookback_days()` 非整数抛出原生 `ValueError` — fixed: 包装为带 `[awin_collector]` 上下文的 `RuntimeError` [`awin_collector.py:77-82`]
- [x] [Review][Patch] F6: 增量模式 `start_date` 参数被静默丢弃 — fixed: 新增 `logger.warning` 提示 [`awin_collector.py:281-284`]
- [x] [Review][Defer] D1: full 模式先 reset 后 fetch，crash 窗口内水位线永久清零 [`awin_collector.py:247-248`] — deferred，spec 明确要求"先 reset"（Key 易错点 #6），属设计决策
- [x] [Review][Defer] D2: `end_date` 可早于 `effective_start`（显式传入历史 end_date + 大回溯窗口）产生倒序日期范围 [`awin_collector.py:276`] — deferred，调用方责任，当前 AC 未覆盖此场景
- [x] [Review][Defer] D3: `datetime.utcnow()` 在 Python 3.12+ 已废弃，timezone-naive [`awin_collector.py:283,288`] — deferred，当前运行环境 Python 3.11，暂不影响

---

## CC#4 变更记录（2026-04-17）

**变更来源：** Sprint Change Proposal CC#4 — ODS 全字段补全 + 速率限制 + EARLIEST_DATE 统一

### 变更内容

1. **ODS 表字段补全（ARCH14）**
   - `ods_awin_transactions` 字段从 5 个补全至 23 个
   - 新增：`publisher_name`、`commission_status`、`click_ref`、`validation_date`、`transaction_type`、`commission_group_id/name`、`aov`、`clicks`、`impressions`、`conversion_rate`、`cpa`、`cpc`、`roi`、`total_commission`、`total_transactions`、`total_value`
   - 权威 DDL 定义已迁移至 `init_doris_tables.py`

2. **全量起始时间统一（ARCH16）**
   - `AWIN_EARLIEST_DATE` 默认值从 `"2024-01-01"` 改为 `"2026-03-01"`

3. **速率限制（ARCH15）**
   - `_fetch_transactions` 翻页循环加 `time.sleep(0.2)`
