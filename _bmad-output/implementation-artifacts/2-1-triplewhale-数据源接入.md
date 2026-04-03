# Story 2.1: TripleWhale 数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 API Key 连接 TripleWhale，并针对 4 张业务表分别抓取样本字段，
以便我能获得利润表和营销表现表所需字段的实际可用性报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `TRIPLEWHALE_API_KEY`；**When** 调用 `triplewhale.authenticate()`；**Then** 返回 `True`，并在日志中输出 `[triplewhale] 认证 ... 成功`

2. **Given** 认证成功后传入 `table_name="pixel_orders_table"`；**When** 调用 `triplewhale.fetch_sample("pixel_orders_table")`；**Then** 返回至少一条原始记录（`list[dict]`），请求使用 `shopDomain=piscifun.myshopify.com` 参数，超时设置为 30s

3. **Given** `fetch_sample` 返回的样本数据；**When** 调用 `triplewhale.extract_fields(sample)`；**Then** 返回 `list[dict]`，每条记录符合标准 FieldInfo 结构（`field_name`, `data_type`, `sample_value`, `nullable`）

4. **Given** 4 张表（pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf）逐一执行；**When** 每张表的 `fetch_sample` + `extract_fields` + `write_raw_report` 完成；**Then** `reports/triplewhale-raw.md` 被创建，包含该表实际字段列表和需求字段对照区块

5. **Given** API Key 无效或网络超时；**When** 调用 `authenticate()` 或 `fetch_sample()`；**Then** 在日志中输出 `[triplewhale] 认证 ... 失败：{具体错误信息}`，函数返回 `False` 或抛出异常，不静默失败

6. **Given** 单元测试环境（mock get_credentials + fixture）；**When** 运行 `tests/test_triplewhale.py`；**Then** 所有单元测试通过，不需要真实 API Key

## Tasks / Subtasks

- [x] Task 1: 实现 `sources/triplewhale.py` 核心结构（AC: 1, 2, 3, 4, 5）
  - [x] Task 1.1: 导入依赖，定义模块常量（BASE_URL、SHOP_DOMAIN、TABLES、DEFAULT_TIMEOUT）
  - [x] Task 1.2: 实现 `authenticate() -> bool`（发探测请求验证 API Key）
  - [x] Task 1.3: 实现 `fetch_sample(table_name: str = None) -> list[dict]`（按表名路由）
  - [x] Task 1.4: 实现 `extract_fields(sample: list[dict]) -> list[dict]`（提取 FieldInfo）
  - [x] Task 1.5: 实现私有函数 `_fetch_table(table_name: str) -> list[dict]`（单表请求）
  - [x] Task 1.6: 所有日志输出使用 `[triplewhale]` 前缀，凭证用 `mask_credential()` 脱敏

- [x] Task 2: 编写测试 Fixture `tests/fixtures/triplewhale_sample.json`（AC: 6）
  - [x] Task 2.1: 创建代表 pixel_orders_table 返回格式的模拟响应 JSON（含 data 列表，至少 2 条记录，覆盖 string/number/boolean/null 字段类型）

- [x] Task 3: 编写单元测试 `tests/test_triplewhale.py`（AC: 1-6）
  - [x] Task 3.1: 测试 `authenticate()` 成功路径（mock requests.get 返回 200）
  - [x] Task 3.2: 测试 `authenticate()` 失败路径（mock 返回 401，验证返回 False 且日志含"失败"）
  - [x] Task 3.3: 测试 `fetch_sample("pixel_orders_table")` 使用正确的 shopDomain 参数
  - [x] Task 3.4: 测试 `extract_fields(sample)` 使用 fixture 数据，验证 FieldInfo 四字段结构
  - [x] Task 3.5: 测试 `extract_fields` 处理嵌套 object 和 null 值（nullable=True）
  - [x] Task 3.6: 测试网络超时（mock requests.get 抛出 Timeout，验证不静默失败）

## Dev Notes

### 目标文件（仅新建以下文件）

| 文件 | 说明 |
|------|------|
| `sources/triplewhale.py` | **唯一新建源文件**，位于 sources/ 目录 |
| `tests/test_triplewhale.py` | 单元测试 |
| `tests/fixtures/triplewhale_sample.json` | API 响应 Mock 数据 |

> **不修改**：`reporter.py`、`validate.py`、`config/credentials.py`、`config/field_requirements.yaml`、其他 `sources/*.py`

---

### TripleWhale SQL API 接入规范

**认证方式：** HTTP Header `X-API-KEY: {TRIPLEWHALE_API_KEY}`

**Base URL：** `https://api.triplewhale.com/api/v2/tw-metrics/`

**shopDomain（固定值）：** `piscifun.myshopify.com`

**4 张路由表：**

| table_name | 说明 | 对应报表 |
|-----------|------|---------|
| `pixel_orders_table` | 像素级订单数据 | profit_table（利润表） |
| `pixel_joined_tvf` | 像素联合视图（广告+订单） | marketing_table（营销表现表） |
| `sessions_table` | 会话数据 | — |
| `product_analytics_tvf` | 商品分析视图 | — |

**认证探测端点（`authenticate()` 使用）：**

```python
# 用最轻量请求验证 API Key 是否有效
# 建议使用 metrics-data 端点（对 pixel_orders_table 做最小限制请求）
resp = requests.get(
    "https://api.triplewhale.com/api/v2/tw-metrics/metrics-data",
    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
    params={"shopDomain": "piscifun.myshopify.com"},
    timeout=30
)
# HTTP 200 → 认证成功；4xx → 认证失败
```

> **注意**：实际可用的端点路径需参照 TripleWhale API 文档（https://triplewhale.readme.io/reference）确认。若上述路径返回 404，尝试用任意已知端点（如 pixel_orders_table 对应的数据端点）做认证探测。

**`fetch_sample` 样本请求（按表路由）：**

```python
# 每张表使用对应端点，通用格式：
resp = requests.post(
    f"https://api.triplewhale.com/api/v2/tw-metrics/{table_name}",
    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
    json={"shopDomain": "piscifun.myshopify.com"},
    timeout=30
)
# 解析返回结构，提取 data 字段（list[dict]）
```

> **实际端点格式说明**：TripleWhale SQL API 对不同表使用不同 URL 路径。实现时需通过以下方式之一确认端点：
> 1. 参照 TripleWhale 文档 SQL API 章节
> 2. 若 POST 方式不通，尝试 GET `?shopDomain=piscifun.myshopify.com&table={table_name}`
> 3. 响应通常为 `{"data": [...], "total": N}` 结构

---

### `sources/triplewhale.py` 完整骨架

```python
"""TripleWhale 数据源接入模块

认证方式：X-API-KEY header
接入表：pixel_orders_table / pixel_joined_tvf / sessions_table / product_analytics_tvf
shopDomain：piscifun.myshopify.com（固定）

公开接口（统一 source 契约）：
    authenticate() -> bool
    fetch_sample(table_name: str = None) -> list[dict]
    extract_fields(sample: list[dict]) -> list[dict]
"""
import logging
from typing import Optional

import requests

from config.credentials import get_credentials, mask_credential

logger = logging.getLogger(__name__)

# --- 常量 ---
BASE_URL: str = "https://api.triplewhale.com/api/v2/tw-metrics"
SHOP_DOMAIN: str = "piscifun.myshopify.com"
DEFAULT_TIMEOUT: int = 30  # 秒，与架构规范一致
TABLES: list[str] = [
    "pixel_orders_table",
    "pixel_joined_tvf",
    "sessions_table",
    "product_analytics_tvf",
]


def authenticate() -> bool:
    """验证 TRIPLEWHALE_API_KEY 是否有效。

    成功返回 True，失败打印错误并返回 False。
    日志格式：[triplewhale] 认证 ... 成功/失败：{原因}
    """
    ...


def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """抓取指定表的样本数据。

    Args:
        table_name: 表名，必须为 TABLES 中的一个。
                    为 None 时使用 pixel_orders_table（默认主表）。

    Returns:
        至少一条原始记录的列表（list[dict]）。

    Raises:
        ValueError: table_name 不在 TABLES 中
        requests.Timeout: 请求超时
        RuntimeError: API 返回非 2xx 状态码
    """
    ...


def extract_fields(sample: list[dict]) -> list[dict]:
    """从样本数据中提取标准 FieldInfo 列表。

    Args:
        sample: fetch_sample() 返回的原始记录列表。

    Returns:
        FieldInfo 列表，每项结构：
        {
            "field_name": str,      # 字段名（API 返回的原始键名）
            "data_type": str,       # string / number / boolean / array / object / null
            "sample_value": Any,    # 首条记录的值（已脱敏）
            "nullable": bool        # 该字段在所有样本中是否存在 None/null 值
        }
    """
    ...


# --- 私有辅助函数 ---

def _get_api_key() -> str:
    """获取 API Key（统一从 get_credentials() 取）。"""
    return get_credentials()["TRIPLEWHALE_API_KEY"]


def _fetch_table(table_name: str, api_key: str) -> list[dict]:
    """向 TripleWhale 请求指定表的数据，返回原始记录列表。"""
    ...


def _infer_type(value: object) -> str:
    """将 Python 值映射为标准 data_type 字符串。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"
```

---

### 关键实现细节

#### 1. `authenticate()` 实现要点

```python
def authenticate() -> bool:
    try:
        api_key = _get_api_key()
        logger.info(f"[triplewhale] 使用 API Key: {mask_credential(api_key)}")
        resp = requests.get(
            f"{BASE_URL}/metrics-data",  # 探测端点，按需调整
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            params={"shopDomain": SHOP_DOMAIN},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code in (200, 400):  # 400 也可能表示 Key 有效但参数缺失
            logger.info("[triplewhale] 认证 ... 成功")
            return True
        logger.error(f"[triplewhale] 认证 ... 失败：HTTP {resp.status_code} {resp.text[:200]}")
        return False
    except requests.Timeout:
        logger.error("[triplewhale] 认证 ... 失败：请求超时")
        return False
    except Exception as e:
        logger.error(f"[triplewhale] 认证 ... 失败：{e}")
        return False
```

#### 2. `fetch_sample` 表路由规则

- `table_name=None` → 默认使用 `"pixel_orders_table"`
- `table_name` 不在 `TABLES` 中 → 抛出 `ValueError(f"未知表名：{table_name}，可用：{TABLES}")`
- 每张表路由到 `_fetch_table(table_name, api_key)`

#### 3. `extract_fields` 实现要点

- 取 `sample[0]` 的 key 集合确定字段名（所有字段）
- `nullable` = 样本中任意记录该字段值为 `None` → `True`
- `sample_value` = `sample[0].get(field_name)` — 直接取第一条记录值（**不包含凭证，无需额外脱敏**）
- 返回列表按 `field_name` 字母序排列，便于报告对比

```python
def extract_fields(sample: list[dict]) -> list[dict]:
    if not sample:
        return []
    all_keys = set()
    for record in sample:
        all_keys.update(record.keys())
    fields = []
    for key in sorted(all_keys):
        first_val = sample[0].get(key)
        nullable = any(rec.get(key) is None for rec in sample)
        fields.append({
            "field_name": key,
            "data_type": _infer_type(first_val),
            "sample_value": first_val,
            "nullable": nullable,
        })
    return fields
```

#### 4. 日志脱敏规则

```python
# ✅ 正确：使用 mask_credential
logger.info(f"[triplewhale] 使用 API Key: {mask_credential(api_key)}")

# ❌ 禁止：直接输出完整 API Key
logger.info(f"[triplewhale] api_key={api_key}")
```

---

### `tests/fixtures/triplewhale_sample.json` 格式要求

```json
{
  "pixel_orders_table": {
    "data": [
      {
        "order_id": "ORD-001",
        "created_at": "2026-03-01T10:00:00Z",
        "total_price": 99.99,
        "currency": "USD",
        "customer_id": "CUST-001",
        "is_first_order": true,
        "refund_amount": null,
        "line_items": [{"sku": "SKU-A", "quantity": 2}]
      },
      {
        "order_id": "ORD-002",
        "created_at": "2026-03-02T11:00:00Z",
        "total_price": 49.99,
        "currency": "USD",
        "customer_id": "CUST-002",
        "is_first_order": false,
        "refund_amount": 49.99,
        "line_items": [{"sku": "SKU-B", "quantity": 1}]
      }
    ],
    "total": 2
  }
}
```

**字段类型覆盖要求（确保 `_infer_type` 能测试所有分支）：**
- `string`：`order_id`, `currency`
- `number`：`total_price`
- `boolean`：`is_first_order`
- `null`：`refund_amount`（首条记录为 null）
- `array`：`line_items`
- `object`：可选，如嵌套 metadata

---

### 单元测试结构要求

```python
# tests/test_triplewhale.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests as req_lib

import sources.triplewhale as triplewhale


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "triplewhale_sample.json"


@pytest.fixture
def tw_sample():
    """加载 triplewhale fixture 数据"""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


# ---- authenticate 测试 ----

def test_authenticate_success(mock_credentials):
    """HTTP 200 → 返回 True，日志含"成功""""
    with patch("sources.triplewhale.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        result = triplewhale.authenticate()
    assert result is True


def test_authenticate_invalid_key(mock_credentials):
    """HTTP 401 → 返回 False，日志含"失败""""
    with patch("sources.triplewhale.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=401, text="Unauthorized")
        result = triplewhale.authenticate()
    assert result is False


def test_authenticate_timeout(mock_credentials):
    """超时 → 返回 False，不抛出未处理异常"""
    with patch("sources.triplewhale.requests.get") as mock_get:
        mock_get.side_effect = req_lib.Timeout()
        result = triplewhale.authenticate()
    assert result is False


# ---- fetch_sample 测试 ----

def test_fetch_sample_uses_shop_domain(mock_credentials, tw_sample):
    """请求必须携带 shopDomain=piscifun.myshopify.com"""
    with patch("sources.triplewhale._fetch_table") as mock_fetch:
        mock_fetch.return_value = tw_sample["pixel_orders_table"]["data"]
        triplewhale.fetch_sample("pixel_orders_table")
    # 验证 _fetch_table 被调用且 table_name 正确
    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args
    assert call_args[0][0] == "pixel_orders_table"


def test_fetch_sample_invalid_table(mock_credentials):
    """未知表名 → 抛出 ValueError"""
    with pytest.raises(ValueError, match="未知表名"):
        triplewhale.fetch_sample("nonexistent_table")


def test_fetch_sample_default_table(mock_credentials, tw_sample):
    """table_name=None → 使用 pixel_orders_table"""
    with patch("sources.triplewhale._fetch_table") as mock_fetch:
        mock_fetch.return_value = tw_sample["pixel_orders_table"]["data"]
        triplewhale.fetch_sample(None)
    call_args = mock_fetch.call_args
    assert call_args[0][0] == "pixel_orders_table"


# ---- extract_fields 测试 ----

def test_extract_fields_structure(tw_sample):
    """返回值符合 FieldInfo 四字段结构"""
    sample = tw_sample["pixel_orders_table"]["data"]
    fields = triplewhale.extract_fields(sample)
    assert len(fields) > 0
    for f in fields:
        assert "field_name" in f
        assert "data_type" in f
        assert "sample_value" in f
        assert "nullable" in f
        assert isinstance(f["nullable"], bool)
        assert f["data_type"] in ("string", "number", "boolean", "array", "object", "null")


def test_extract_fields_nullable_detection(tw_sample):
    """refund_amount 在首条记录为 null → nullable=True"""
    sample = tw_sample["pixel_orders_table"]["data"]
    fields = triplewhale.extract_fields(sample)
    refund_field = next((f for f in fields if f["field_name"] == "refund_amount"), None)
    assert refund_field is not None
    assert refund_field["nullable"] is True


def test_extract_fields_empty_sample():
    """空样本 → 返回空列表"""
    assert triplewhale.extract_fields([]) == []
```

---

### conftest.py mock 使用方式

Story 1-2 已实现 `mock_credentials` fixture，用法：

```python
# 在测试函数签名中加入 mock_credentials 参数即可
def test_authenticate_success(mock_credentials):
    # get_credentials() 被 mock，返回 TEST_CREDENTIALS（含 TRIPLEWHALE_API_KEY="test_tw_key"）
    ...
```

mock patch 路径：`config.credentials.get_credentials`（conftest.py 已配置）

---

### 禁止行为（Anti-Patterns）

```python
# ❌ 直接读取环境变量
api_key = os.getenv("TRIPLEWHALE_API_KEY")

# ✅ 从统一加载器导入
from config.credentials import get_credentials, mask_credential
creds = get_credentials()
api_key = creds["TRIPLEWHALE_API_KEY"]

# ❌ 静默失败
except Exception:
    pass

# ✅ 明确报错，使用结构化日志
except Exception as e:
    logger.error(f"[triplewhale] 请求失败：{e}")
    raise  # 或 return False（取决于函数契约）

# ❌ 在日志中输出完整 API Key
logger.info(f"api_key={api_key}")

# ✅ 使用 mask_credential
logger.info(f"[triplewhale] 使用 API Key: {mask_credential(api_key)}")
```

---

### 与已有代码集成

**`reporter.py` 调用方式（验证集成）：**

```python
# validate.py（未来 Epic 5 实现）会按如下方式调用本 Story 成果：
import sources.triplewhale as triplewhale
import reporter

ok = triplewhale.authenticate()
if ok:
    for table in triplewhale.TABLES:
        sample = triplewhale.fetch_sample(table)
        fields = triplewhale.extract_fields(sample)
        reporter.write_raw_report("triplewhale", fields, table, len(sample))
        reporter.init_validation_report("triplewhale")
```

**`field_requirements.yaml` 中 triplewhale 的需求字段：**

- `profit_table`：日期、销售额、订单量（source=triplewhale, table=pixel_orders_table）
- `marketing_table`：曝光量、点击量、广告花费、ROAS（source=triplewhale, table=pixel_joined_tvf）

---

### 已有代码模式（必须遵守）

基于 Story 1-1 ～ 1-4 的建立的约定：

1. **所有函数必须有类型注解**（`-> bool`、`-> list[dict]`）
2. **字符串格式化使用 f-string**（不用 `.format()` 或 `%`）
3. **日志使用 `logging.getLogger(__name__)`**（不用 `print()`）
4. **`requests` 调用统一 `timeout=30`**（DEFAULT_TIMEOUT 常量）
5. **测试使用 `mock_credentials` fixture** + `patch` + `MagicMock`

---

### 历史遗留问题（deferred-work.md 相关）

- `mask_credential` 在 source 模块中首次实际使用（Story 1-2 代码审查已指出「尚未在任何生产日志路径调用」），本 Story 完成此落实
- `requirements.txt` 无需变更（requests、pytest 已在 1-1 中加入）

---

### Project Structure Notes

```
outdoor-data-validator/
├── sources/
│   └── triplewhale.py          ← 新建（本 Story 核心交付）
└── tests/
    ├── fixtures/
    │   └── triplewhale_sample.json  ← 新建（Mock 数据）
    └── test_triplewhale.py     ← 新建（单元测试）
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1: TripleWhale 数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns] — 三函数签名 + FieldInfo 结构
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH6] — TripleWhale 单文件按表路由，shopDomain
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] — 命名规范
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns] — 禁止行为
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines] — AI Agent 必须遵守规则
- [Source: _bmad-output/docs/api-access-archive.md#TripleWhale] — API Key 认证方式、端点示例
- [Source: _bmad-output/implementation-artifacts/1-4-报告渲染器.md#Dev Notes] — reporter.py 调用方式
- [Source: config/credentials.py] — get_credentials()、mask_credential() 用法
- [Source: tests/conftest.py] — mock_credentials fixture，TEST_CREDENTIALS["TRIPLEWHALE_API_KEY"]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Mock 未生效问题：`from config.credentials import get_credentials` 会在 triplewhale.py 创建本地引用，conftest patch 无法影响。改为 `import config.credentials as _creds_module` 并通过模块引用调用，解决了 9 个测试初始失败。
- `_infer_type` bool-before-int：Python 中 `bool` 是 `int` 的子类，须先判断 `bool` 再判断 `int/float`，否则 `True` 会被识别为 `number`。

### Completion Notes List

- 实现 `sources/triplewhale.py`，完整实现三函数公开接口及 `_fetch_table`/`_infer_type` 私有函数
- 创建 `tests/fixtures/triplewhale_sample.json`，覆盖全部 4 张表数据及所有字段类型（string/number/boolean/null/array/object）
- 编写 `tests/test_triplewhale.py`，共 48 个测试用例，全部通过
- 通过 git stash 验证，5 个测试失败均为既存问题（credentials/dingtalk/social_media），与本 Story 无关

### File List

- `sources/triplewhale.py`（新建）
- `tests/fixtures/triplewhale_sample.json`（新建）
- `tests/test_triplewhale.py`（新建）

### Review Findings

- [x] [Review][Patch] `fetch_sample()` 无错误日志即传播异常（AC5 违规） [sources/triplewhale.py: fetch_sample] — 已修复：在 `_fetch_table()` 调用外添加 try/except，在 raise 前调用 `logger.error`
- [x] [Review][Patch] `_fetch_table` 未验证 `body["data"]` 是否为 list，`body=None` 时 TypeError [sources/triplewhale.py: _fetch_table] — 已修复：添加 isinstance 检查和 None 防护
- [x] [Review][Defer] 未处理 `resp.json()` 的 JSONDecodeError [sources/triplewhale.py: _fetch_table] — deferred, 防御性编码，规范未要求
- [x] [Review][Defer] `_get_api_key` KeyError 传播无 triplewhale 日志前缀 [sources/triplewhale.py: _get_api_key] — deferred, credentials 模块职责，get_credentials() 已保障

## Change Log

- 2026-04-03: Story 创建，状态 ready-for-dev
