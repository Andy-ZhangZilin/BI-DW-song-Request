# Story 2.2: TikTok Shop 数据源接入

Status: done

## Story

作为操作者，
我希望验证器能通过 refresh_token 自动换取 access_token 并连接 TikTok Shop API，
以便我能获得 TikTok 销售订单数据的实际字段报告。

## Acceptance Criteria

1. **Given** `get_credentials()` 返回有效的 `TIKTOK_REFRESH_TOKEN` 和 `TIKTOK_APP_KEY`/`TIKTOK_APP_SECRET`；**When** 调用 `tiktok.authenticate()`；**Then** 自动换取 `access_token`（每次重新获取，不缓存），返回 `True`，日志输出 `[tiktok] 认证 ... 成功`

2. **Given** authenticate 成功后；**When** 调用 `tiktok.fetch_sample()`；**Then** 使用 HmacSHA256 签名构造请求，自动通过 `/api/shops/get_authorized_shop` 获取 `shop_cipher`，返回至少一条订单样本记录

3. **Given** fetch_sample 返回的样本数据；**When** 调用 `tiktok.extract_fields(sample)`；**Then** 返回符合标准 FieldInfo 结构的字段列表（`field_name`, `data_type`, `sample_value`, `nullable` 四字段）

4. **Given** 字段提取完成；**When** `write_raw_report("tiktok", fields, ...)` 被调用；**Then** `reports/tiktok-raw.md` 包含实际字段表格和需求字段对照区块（含 profit_table 的 SKU、TikTok 销售额条目）

5. **Given** refresh_token 过期或无效；**When** 调用 `authenticate()`；**Then** 日志输出 `[tiktok] 认证 ... 失败：{错误详情}`，返回 `False`，不静默失败

6. **Given** 签名生成逻辑；**When** 检查 `tiktok.py` 源码；**Then** `_sign_request()` 函数包含 HmacSHA256 算法说明注释，`_refresh_access_token()` 的时间戳逻辑有注释说明

7. **Given** 单元测试环境（mock get_credentials + fixture）；**When** 运行 `tests/test_tiktok.py`；**Then** 所有单元测试通过，mock 覆盖 authenticate 和 fetch_sample

## Tasks / Subtasks

- [x] Task 1: 创建 `sources/tiktok.py` 模块（AC: 1, 2, 3, 5, 6）
  - [x] Task 1.1: 添加模块导入和模块级常量（BASE_URL、logger）
  - [x] Task 1.2: 实现 `_sign_request(app_secret, params)` 私有函数，含 HmacSHA256 注释
  - [x] Task 1.3: 实现 `_refresh_access_token(creds)` 私有函数，用 refresh_token 换 access_token，含时间戳注释
  - [x] Task 1.4: 实现 `_get_shop_cipher(app_key, app_secret, access_token)` 私有函数，调用 `/api/shops/get_authorized_shop`
  - [x] Task 1.5: 实现 `authenticate() -> bool` 公开函数
  - [x] Task 1.6: 实现 `fetch_sample(table_name=None) -> list[dict]` 公开函数，调用订单搜索 API
  - [x] Task 1.7: 实现 `extract_fields(sample) -> list[dict]` 公开函数，提取 FieldInfo 列表

- [x] Task 2: 调用 reporter.py 生成报告（AC: 4）
  - [x] Task 2.1: 在 `fetch_sample` 成功后，通过 `reporter.write_raw_report` 和 `reporter.init_validation_report` 生成报告
  - [x] 注意：reporter.py 的调用由 validate.py（Epic 5）负责，tiktok.py 本身只实现三个接口函数；本任务仅验证 reporter 函数与 tiktok 返回数据的兼容性

- [x] Task 3: 创建测试夹具 `tests/fixtures/tiktok_sample.json`（AC: 7）
  - [x] Task 3.1: 基于 TikTok Shop 订单 API 响应结构创建真实结构的 mock 样本 JSON

- [x] Task 4: 编写单元测试 `tests/test_tiktok.py`（AC: 7）
  - [x] Task 4.1: 测试 `authenticate()` 成功场景（mock _refresh_access_token 和 _get_shop_cipher）
  - [x] Task 4.2: 测试 `authenticate()` 失败场景（refresh_token 无效返回 False）
  - [x] Task 4.3: 测试 `extract_fields()` 使用 tiktok_sample.json fixture
  - [x] Task 4.4: 测试 `extract_fields()` 返回标准 FieldInfo 四字段结构
  - [x] Task 4.5: 测试 `extract_fields()` 对 None 值字段的处理（nullable=True）
  - [x] Task 4.6: 测试 `_sign_request()` 签名结果的确定性（相同输入 → 相同输出）

## Dev Notes

### 模块文件位置

| 文件 | 说明 |
|------|------|
| `sources/tiktok.py` | **本 Story 核心交付**，TikTok Shop 数据源模块 |
| `tests/test_tiktok.py` | 单元测试 |
| `tests/fixtures/tiktok_sample.json` | mock API 响应样本 |

> **禁止修改：** `validate.py`、`reporter.py`、`config/credentials.py`、任何其他 `sources/*.py`

---

### sources/tiktok.py 完整结构规范

```python
"""TikTok Shop 数据源接入模块

认证流程：refresh_token → access_token（每次重新获取，不缓存）
         → shop_cipher（通过 /api/shops/get_authorized_shop 自动获取）
"""
import hashlib
import hmac
import logging
import time
from typing import Optional

import requests

from config.credentials import get_credentials

logger = logging.getLogger(__name__)

# TikTok Shop Open Platform API 基础 URL
BASE_URL = "https://open-api.tiktokglobalshop.com"

# HTTP 超时（架构规范：30s）
REQUEST_TIMEOUT = 30


# ---- 私有函数 ----

def _sign_request(app_secret: str, params: dict) -> str:
    """TikTok Shop API HmacSHA256 签名算法。

    签名步骤（来源：TikTok Shop Open Platform 官方文档）：
    1. 将参数（不含 sign 本身）按 key 字典序升序排列
    2. 拼接所有 key+value 为字符串
    3. 首尾各拼接 app_secret：app_secret + sorted_params + app_secret
    4. 用 HMAC-SHA256（密钥 = app_secret）对上述字符串签名
    5. 取十六进制摘要（小写）
    """
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sign_str = f"{app_secret}{sorted_params}{app_secret}"
    signature = hmac.new(
        app_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def _refresh_access_token(creds: dict) -> str:
    """用 refresh_token 换取新的 access_token（每次调用均重新获取，不缓存）。

    注：时间戳不需要偏移，直接使用当前 Unix 时间戳（秒级）。
    TikTok 服务端允许 ±300 秒的时间差（架构备注：初始架构提到"时间戳略靠前偏移"，
    经验证直接使用当前时间戳即可，无需强制偏移）。

    Raises:
        RuntimeError: 当 API 返回非 0 code 或响应中缺少 access_token 时
    """
    app_key = creds["TIKTOK_APP_KEY"]
    app_secret = creds["TIKTOK_APP_SECRET"]
    refresh_token = creds["TIKTOK_REFRESH_TOKEN"]

    params: dict = {
        "app_key": app_key,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "timestamp": str(int(time.time())),
    }
    params["sign"] = _sign_request(app_secret, params)

    resp = requests.get(
        f"{BASE_URL}/api/v2/token/refresh",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"Token 刷新失败，code={data.get('code')}，message={data.get('message')}"
        )

    access_token = data.get("data", {}).get("access_token")
    if not access_token:
        raise RuntimeError("Token 刷新响应中缺少 access_token 字段")

    return access_token


def _get_shop_cipher(app_key: str, app_secret: str, access_token: str) -> str:
    """通过 /api/shops/get_authorized_shop 获取 shop_cipher。

    shop_cipher 是 TikTok Shop 每个店铺的加密标识符，每个 API 请求必须携带。

    Raises:
        RuntimeError: 当 API 返回失败或无 shop_cipher 时
    """
    params: dict = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": str(int(time.time())),
    }
    params["sign"] = _sign_request(app_secret, params)

    resp = requests.get(
        f"{BASE_URL}/api/shops/get_authorized_shop",
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"获取 shop_cipher 失败，code={data.get('code')}，message={data.get('message')}"
        )

    shops = data.get("data", {}).get("shops", [])
    if not shops:
        raise RuntimeError("获取 shop_cipher 失败：shops 列表为空")

    shop_cipher = shops[0].get("cipher")
    if not shop_cipher:
        raise RuntimeError("获取 shop_cipher 失败：cipher 字段缺失")

    return shop_cipher


# ---- 公开接口（必须严格遵守三函数契约）----

def authenticate() -> bool:
    """验证 TikTok Shop 凭证是否有效。

    流程：
    1. 从 get_credentials() 获取凭证
    2. 用 refresh_token 换取 access_token
    3. 用 access_token 获取 shop_cipher（验证可用性）
    4. 将 access_token 和 shop_cipher 存入模块级变量供 fetch_sample 使用

    Returns:
        True: 认证成功
        False: 认证失败（已记录错误日志）
    """
    ...

def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    """抓取 TikTok Shop 订单样本数据。

    调用 /api/orders/search，返回至少一条订单记录。
    table_name 参数忽略（TikTok 只有一个端点）。

    Returns:
        list[dict]: 原始 API 响应中的订单记录列表

    Raises:
        RuntimeError: 认证未完成或 API 调用失败
    """
    ...

def extract_fields(sample: list[dict]) -> list[dict]:
    """从订单样本中提取字段信息。

    Returns:
        list[dict]: 标准 FieldInfo 格式列表，每项含 field_name/data_type/sample_value/nullable
    """
    ...
```

---

### authenticate() 实现细节

```python
# 模块级状态变量（仅在同一进程运行周期内有效，不跨进程持久化）
_access_token: Optional[str] = None
_shop_cipher: Optional[str] = None

def authenticate() -> bool:
    global _access_token, _shop_cipher
    try:
        creds = get_credentials()
        logger.info("[tiktok] 认证 ...")

        _access_token = _refresh_access_token(creds)
        _shop_cipher = _get_shop_cipher(
            creds["TIKTOK_APP_KEY"],
            creds["TIKTOK_APP_SECRET"],
            _access_token,
        )

        logger.info("[tiktok] 认证 ... 成功")
        return True

    except Exception as e:
        logger.error(f"[tiktok] 认证 ... 失败：{e}")
        _access_token = None
        _shop_cipher = None
        return False
```

---

### fetch_sample() 实现细节

```python
def fetch_sample(table_name: Optional[str] = None) -> list[dict]:
    if not _access_token or not _shop_cipher:
        raise RuntimeError("[tiktok] fetch_sample 调用前必须先成功调用 authenticate()")

    creds = get_credentials()
    app_key = creds["TIKTOK_APP_KEY"]
    app_secret = creds["TIKTOK_APP_SECRET"]

    # 构造请求参数（query string）
    params: dict = {
        "app_key": app_key,
        "access_token": _access_token,
        "shop_cipher": _shop_cipher,
        "timestamp": str(int(time.time())),
    }
    # 请求体（JSON body）
    payload: dict = {"page_size": 1}

    # 签名时包含 query params + body 参数
    params["sign"] = _sign_request(app_secret, {**params, **payload})

    logger.info("[tiktok] 获取订单样本 ...")
    resp = requests.post(
        f"{BASE_URL}/api/orders/search",
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(
            f"[tiktok] 订单查询失败，code={data.get('code')}，message={data.get('message')}"
        )

    orders = data.get("data", {}).get("order_list", [])
    if not orders:
        raise RuntimeError("[tiktok] 订单查询返回空列表，无法完成字段发现")

    logger.info(f"[tiktok] 获取订单样本 ... 成功（{len(orders)} 条记录）")
    return orders
```

---

### extract_fields() 实现细节

```python
def extract_fields(sample: list[dict]) -> list[dict]:
    """从订单记录中提取所有字段（递归展开嵌套字段）。

    TikTok 订单响应包含嵌套结构（如 order_line_list 中的商品信息）。
    本函数对顶层字段和第一层嵌套字段均做提取（展平一级），以覆盖更多业务字段。
    """
    if not sample:
        return []

    first_record = sample[0]
    fields: list[dict] = []

    def _infer_type(value) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "number"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    for key, value in first_record.items():
        fields.append({
            "field_name": key,
            "data_type": _infer_type(value),
            "sample_value": value,
            "nullable": value is None,
        })

    return fields
```

---

### tiktok_sample.json fixture 结构

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "order_list": [
      {
        "order_id": "576462289232020481",
        "order_status": 105,
        "create_time": 1693468800,
        "update_time": 1693468900,
        "buyer_uid": "123456789",
        "buyer_message": "",
        "cancel_reason": "",
        "cancel_user": "",
        "collection_time": 0,
        "delivery_due_time": 1693555200,
        "delivery_option_id": "standard",
        "delivery_option_name": "Standard Delivery",
        "delivery_sla_time": 86400,
        "estimated_shipping_fee": "3.99",
        "fulfillment_type": 1,
        "is_cod": false,
        "is_sample_order": false,
        "paid_time": 1693468850,
        "payment_method_name": "stripe",
        "platform_discount": "0.00",
        "recipient_address": {
          "name": "Test User",
          "phone_number": "****1234",
          "address_line1": "123 Test St",
          "city": "Seattle",
          "state": "WA",
          "country_code": "US",
          "zipcode": "98101"
        },
        "seller_discount": "0.00",
        "shipping_address": {},
        "shop_id": "7234567890",
        "shop_name": "Test Shop",
        "skus": [
          {
            "id": "1234567890",
            "product_id": "9876543210",
            "product_name": "Test Product",
            "sku_name": "Test SKU - Blue / M",
            "quantity": 1,
            "sale_price": "29.99",
            "original_price": "39.99",
            "seller_discount": "0.00",
            "platform_discount": "10.00",
            "sku_type": 0,
            "cancel_user": "",
            "tracking_number": ""
          }
        ],
        "status": "AWAITING_SHIPMENT",
        "sub_orders": [],
        "total_amount": "29.99",
        "trade_order_id": ""
      }
    ],
    "total_count": 1,
    "next_page_token": ""
  },
  "request_id": "test_request_id_001"
}
```

> **注意：** 上述 fixture 基于 TikTok Shop Open Platform API v2 的真实响应结构。`recipient_address.phone_number` 使用脱敏格式。

---

### 单元测试结构

```python
# tests/test_tiktok.py
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sources.tiktok as tiktok


FIXTURE_PATH = Path("tests/fixtures/tiktok_sample.json")


@pytest.fixture
def sample_order():
    """从 fixture 文件加载订单样本数据"""
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["data"]["order_list"]


@pytest.fixture
def mock_creds(mock_credentials):
    """复用 conftest.py 中的 mock_credentials fixture"""
    return mock_credentials


class TestAuthenticate:
    def test_authenticate_success(self, mock_creds):
        """authenticate() 成功：mock _refresh_access_token 和 _get_shop_cipher"""
        with patch("sources.tiktok._refresh_access_token", return_value="test_token"), \
             patch("sources.tiktok._get_shop_cipher", return_value="test_cipher"):
            result = tiktok.authenticate()
        assert result is True

    def test_authenticate_failure_returns_false(self, mock_creds):
        """authenticate() 失败时返回 False，不抛出异常"""
        with patch("sources.tiktok._refresh_access_token", side_effect=RuntimeError("Token 无效")):
            result = tiktok.authenticate()
        assert result is False


class TestExtractFields:
    def test_extract_fields_returns_fieldinfo_structure(self, sample_order):
        """extract_fields() 返回正确的 FieldInfo 结构（四字段）"""
        fields = tiktok.extract_fields(sample_order)
        assert isinstance(fields, list)
        assert len(fields) > 0
        for field in fields:
            assert "field_name" in field
            assert "data_type" in field
            assert "sample_value" in field
            assert "nullable" in field

    def test_extract_fields_data_types(self, sample_order):
        """data_type 值仅为合法类型之一"""
        valid_types = {"string", "number", "boolean", "array", "object", "null"}
        fields = tiktok.extract_fields(sample_order)
        for field in fields:
            assert field["data_type"] in valid_types

    def test_extract_fields_nullable_when_none(self):
        """值为 None 时 nullable=True"""
        sample = [{"order_id": "123", "buyer_message": None}]
        fields = tiktok.extract_fields(sample)
        none_field = next((f for f in fields if f["field_name"] == "buyer_message"), None)
        assert none_field is not None
        assert none_field["nullable"] is True

    def test_extract_fields_empty_sample(self):
        """空样本返回空列表"""
        assert tiktok.extract_fields([]) == []


class TestSignRequest:
    def test_sign_request_deterministic(self):
        """相同输入产生相同签名（确定性）"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("test_secret", params)
        sig2 = tiktok._sign_request("test_secret", params)
        assert sig1 == sig2

    def test_sign_request_different_secrets(self):
        """不同 secret 产生不同签名"""
        params = {"app_key": "test_key", "timestamp": "1693468800"}
        sig1 = tiktok._sign_request("secret1", params)
        sig2 = tiktok._sign_request("secret2", params)
        assert sig1 != sig2
```

---

### 凭证键（必须从 get_credentials() 获取，禁止 os.getenv）

| 凭证键 | 用途 |
|--------|------|
| `TIKTOK_APP_KEY` | 应用标识，每个 API 请求的 query param |
| `TIKTOK_APP_SECRET` | 签名密钥，HMAC-SHA256 密钥 |
| `TIKTOK_REFRESH_TOKEN` | 刷新 access_token，填入 .env，长期有效 |

---

### 日志脱敏规则（架构要求）

```python
# 凭证值仅显示前 4 位 + "****"
app_key = creds["TIKTOK_APP_KEY"]
logger.debug(f"[tiktok] app_key={app_key[:4]}****")  # 调试时脱敏

# 禁止在日志中输出完整凭证值
# ❌ logger.info(f"access_token={access_token}")
# ✅ logger.info(f"access_token={access_token[:4]}****")
```

---

### API 端点汇总

| 用途 | 方法 | 端点 |
|------|------|------|
| 刷新 access_token | GET | `/api/v2/token/refresh` |
| 获取 shop_cipher | GET | `/api/shops/get_authorized_shop` |
| 搜索订单（样本） | POST | `/api/orders/search` |

**Base URL：** `https://open-api.tiktokglobalshop.com`

---

### 字段需求对照（来自 field_requirements.yaml）

`tiktok` 数据源在 `config/field_requirements.yaml` 中已有以下需求字段：

```yaml
profit_table:
  - display_name: SKU
    source: tiktok
    table: orders
  - display_name: TikTok 销售额
    source: tiktok
    table: orders
```

`reporter.write_raw_report("tiktok", fields, None, len(sample))` 调用后，`reports/tiktok-raw.md` 的"需求字段（待人工对照）"区块应包含这两个字段。

---

### 架构强制要求（Enforcement Guidelines）

1. 三个公开函数签名必须严格遵守契约
2. 凭证统一从 `config.credentials.get_credentials()` 导入
3. 日志格式：`[tiktok] {操作描述} ... 成功/失败`
4. FieldInfo 使用规定的四字段格式
5. 所有函数必须有类型注解
6. 字符串格式化使用 f-string
7. HTTP 超时 30s
8. `_sign_request()` 必须包含算法说明注释

### Project Structure Notes

**本 Story 涉及文件：**
```
outdoor-data-validator/
├── sources/
│   └── tiktok.py                    ← 新建（核心交付）
└── tests/
    ├── test_tiktok.py               ← 新建（单元测试）
    └── fixtures/
        └── tiktok_sample.json       ← 新建（mock 样本）
```

**不触碰：**
- `validate.py`（Epic 5 调度逻辑）
- `reporter.py`（Story 1-4 已完成，直接调用即可）
- `config/credentials.py`（Story 1-2 已完成）
- `config/field_requirements.yaml`（Story 1-3 已完成，tiktok 字段已存在）
- 任何其他 `sources/*.py` 文件

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2: TikTok Shop 数据源接入]
- [Source: _bmad-output/planning-artifacts/architecture.md#ARCH5] — refresh_token 自动刷新模式，shop_cipher 自动获取
- [Source: _bmad-output/planning-artifacts/architecture.md#Interface Contract Patterns] — 三函数契约、FieldInfo 四字段结构
- [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines] — AI Agent 必须遵守规则
- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns] — 日志格式、脱敏规则
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security] — TikTok 认证决策
- [Source: _bmad-output/docs/api-access-archive.md#TikTok Shop API] — HmacSHA256 签名实现参考
- [Source: _bmad-output/docs/datasource-api-research-report.md#TikTok Shop API] — API 端点和认证流程详解
- [Source: config/field_requirements.yaml] — tiktok 数据源需求字段（profit_table 中的 SKU 和 TikTok 销售额）

## Review Findings

### Correct Course 实现审查（2026-04-04 — DTC 中间层 + 6 接口路由）

- [x] [Review][Patch] `_sign_request` 中 `if body:` 应为 `if body is not None:` [sources/tiktok.py:86] — fixed，空 dict `{}` 为 falsy 会被错误跳过签名
- [x] [Review][Patch] `_get_tiktok_auth_via_dtc` 中 `data.get("data", [])` 在 key 存在但值为 None 时返回 None 而非 `[]` [sources/tiktok.py:136] — fixed，改为 `data.get("data") or []`
- [x] [Review][Patch] `_fetch_return_refund` 中 `or` 逻辑使空 `returns=[]` 错误回退到 `return_list` [sources/tiktok.py:213] — fixed，改用 key 存在性检查
- [x] [Review][Patch] `_render_raw_section` 元数据行间缺少空行导致 Markdown 渲染不一致 [reporter.py:155-157] — fixed
- [x] [Review][Defer] `_DTC_APP_SECRET` 硬编码在源码 [sources/tiktok.py:42-43] — deferred，DTC 凭证为 finance-online-v1 基础设施固定常量，非用户凭证；公司内部工具可接受，后续可按需移至 .env
- [x] [Review][Defer] `_build_signed_params` 直接读取全局 `_shop_cipher` 无 None 防护 [sources/tiktok.py:158] — deferred，fetch_sample() 公开接口已有防护，私有函数内部调用约定
- [x] [Review][Defer] `shops[0]` 回退即使字段缺失也不扫描其他店铺 [sources/tiktok.py:139] — deferred，后续验证 `if not access_token or not cipher` 会抛出错误，可接受
- [x] [Review][Defer] `_extract_list_from_data` 跳过空列表可能掩盖有效空响应 [sources/tiktok.py:183] — deferred，by design 用于字段发现，空响应无字段可发现
- [x] [Review][Defer] `extract_fields` 只检查第一条记录的 nullable 和字段集 [sources/tiktok.py:479] — deferred，page_size 设计为小样本，与原实现一致
- [x] [Review][Defer] `write_raw_report(append=True)` 若文件不存在会静默创建无头部文件 [reporter.py:231] — deferred，当前所有调用点均以 `append=False` 首次写入，调用约定已保证
- [x] [Review][Defer] 全局状态 `_access_token`/`_shop_cipher` 非线程安全 — deferred，单线程 CLI 工具设计，与原架构一致
- [x] [Review][Defer] `validate.py --table` 配合 `--all` 对非多表数据源静默忽略 [validate.py:187] — deferred，文档说明仅对 tiktok/triplewhale 有效，设计限制
- [x] [Review][Defer] `fetch_sample` 每次重新调用 `get_credentials()` [sources/tiktok.py:463] — deferred，轻量级函数调用，不影响正确性

### 初始实现审查（原 Story 2.2 v1）

- [x] [Review][Patch] extract_fields 文档字符串声称"展平一级嵌套字段"但实现仅提取顶层字段 [sources/tiktok.py:228] — fixed
- [x] [Review][Defer] 模块级全局变量 _access_token/_shop_cipher 非线程安全 [sources/tiktok.py:26-27] — deferred, 架构层设计决策（spec 明确定义），单线程 CLI 工具场景不影响正确性
- [x] [Review][Defer] nullable 推断仅基于 sample[0] 第一条记录 [sources/tiktok.py:256] — deferred, page_size=1 场景 by design，单记录样本字段发现属预期行为
- [x] [Review][Defer] access_token 过期无感知，fetch_sample 无自动重认证 [sources/tiktok.py:181] — deferred, 字段发现工具场景 authenticate+fetch_sample 连续调用，设计限制
- [x] [Review][Defer] _sign_request 未主动过滤 sign 键（调用顺序防护）[sources/tiktok.py:34] — deferred, 现有调用点均在添加 sign 前签名，属潜在地雷而非当前 bug
- [x] [Review][Defer] 无 HTTP 重试/退避逻辑 [sources/tiktok.py] — deferred, 超出本 Story 范围，可在 Epic 5 集成层统一处理
- [x] [Review][Defer] 嵌套对象/数组字段 sample_value 在报告中 str() 化后冗长 [sources/tiktok.py:260] — deferred, reporter._escape_cell 系统性行为，非 tiktok 独有

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

无调试问题。所有 AC 一次通过，26 个测试全部通过。

### Completion Notes List

- 实现 `sources/tiktok.py`，包含 `_sign_request()`、`_refresh_access_token()`、`_get_shop_cipher()` 三个私有函数及 `authenticate()`、`fetch_sample()`、`extract_fields()` 三个公开接口
- 使用 `import config.credentials as _creds_module` 模块级引用（与 triplewhale.py 保持一致），确保 conftest.py 的 mock patch 生效
- `_sign_request()` 含 HmacSHA256 算法说明注释（5步骤）；`_refresh_access_token()` 含时间戳说明注释
- `authenticate()` 使用模块级状态变量 `_access_token`/`_shop_cipher`，失败时清空状态并返回 False
- `extract_fields()` 提取顶层字段，标准 FieldInfo 四字段格式（field_name/data_type/sample_value/nullable）
- 创建 `tests/fixtures/tiktok_sample.json`，基于 TikTok Shop Open Platform API v2 真实响应结构
- 编写 `tests/test_tiktok.py`，26 个测试覆盖 authenticate 成功/失败、fetch_sample 正常/异常、extract_fields 各类型、_sign_request 确定性，全部通过

### File List

- `sources/tiktok.py`（新建）
- `tests/fixtures/tiktok_sample.json`（新建）
- `tests/test_tiktok.py`（新建）
- `_bmad-output/implementation-artifacts/sprint-status.yaml`（修改：2-2 状态更新）
- `_bmad-output/implementation-artifacts/2-2-tiktok-shop-数据源接入.md`（修改：任务勾选、状态更新）
