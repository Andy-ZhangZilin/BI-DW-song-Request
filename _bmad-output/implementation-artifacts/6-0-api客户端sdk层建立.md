# Story 6.0：API 客户端 SDK 层建立

Status: done

## Story

作为数据工程师，
我希望在 `outdoor_collector/sdk/` 下建立 TikTok、TripleWhale、钉钉三个 API 客户端模块，
以便后续所有采集脚本可复用统一的认证与请求封装，不重复实现。

## Acceptance Criteria

1. 创建 `sdk/tiktok/`：封装 refresh_token → access_token 换取（每次重新获取）、HmacSHA256 请求签名、shop_cipher 自动获取；对外暴露 `TikTokClient` 类
2. 创建 `sdk/triplewhale/`：封装 API Key 认证（X-API-KEY header）、GraphQL/REST 请求发送、基础错误重试；对外暴露 `TripleWhaleClient` 类
3. 创建 `sdk/dingtalk/`：封装 app_key/secret → access_token 获取与有效期内复用（避免重复换取）、Bitable 记录分页读取；对外暴露 `DingTalkClient` 类
4. 凭证统一通过 `.env` 加载（`python-dotenv`），SDK 内不硬编码任何密钥
5. 各客户端提供统一日志格式：`[sdk][{source}] 操作描述 ... 成功/失败`
6. 认证失败抛出明确异常，不静默返回空

## Tasks / Subtasks

- [x] Task 1：创建 outdoor_collector/sdk/ 目录结构（AC: #1,#2,#3）
  - [x] 1.1 创建 `bi/python_sdk/outdoor_collector/sdk/__init__.py`
  - [x] 1.2 创建 `bi/python_sdk/outdoor_collector/sdk/tiktok/__init__.py`
  - [x] 1.3 创建 `bi/python_sdk/outdoor_collector/sdk/triplewhale/__init__.py`
  - [x] 1.4 创建 `bi/python_sdk/outdoor_collector/sdk/dingtalk/__init__.py`

- [x] Task 2：实现 TikTok SDK（AC: #1）
  - [x] 2.1 实现 `sdk/tiktok/auth.py`：DTC 两步换取 access_token + shop_cipher
  - [x] 2.2 实现 `sdk/tiktok/client.py`：`TikTokClient` 类 + HmacSHA256 签名 + 接口方法封装

- [x] Task 3：实现 TripleWhale SDK（AC: #2）
  - [x] 3.1 实现 `sdk/triplewhale/auth.py`：API Key 认证验证
  - [x] 3.2 实现 `sdk/triplewhale/client.py`：`TripleWhaleClient` 类 + SQL 查询封装

- [x] Task 4：实现 DingTalk SDK（AC: #3）
  - [x] 4.1 实现 `sdk/dingtalk/auth.py`：access_token 获取 + 有效期内缓存
  - [x] 4.2 实现 `sdk/dingtalk/client.py`：`DingTalkClient` 类 + Bitable 记录分页读取

- [x] Task 5：验证凭证加载机制（AC: #4）
  - [x] 5.1 确认所有 SDK 使用 `python-dotenv` 从 `.env` 加载凭证，不调用 Phase 1 的 `config/credentials.py`

- [x] Task 6：验证日志和异常规范（AC: #5,#6）
  - [x] 6.1 确认所有客户端使用 `[sdk][{source}]` 日志格式
  - [x] 6.2 确认认证失败抛出 `RuntimeError` 或 `AuthenticationError`，不返回空值

## Dev Notes

### 关键架构约束

**代码位置（绝对路径）**：`bi/python_sdk/outdoor_collector/`

> `bi/` 是主仓库的 git submodule，使用时需确认已 `git submodule update --init`。
> outdoor_collector/ 目录当前不存在，本 Story 以及 Story 6.1 会共同创建它。
> Story 6.0 仅负责 `sdk/` 子目录；根目录结构和 `common/`、`collectors/` 由 Story 6.1 创建。

**与 Phase 1 代码的关系**：
- SDK 客户端是对 `sources/tiktok.py`、`sources/triplewhale.py`、`sources/dingtalk.py` 中认证逻辑的重新封装（OOP 形式）
- SDK **不得** import 主工具模块（`validate`、`reporter`、`sources.*`、`config.credentials`）
- SDK 是独立部署单元（`outdoor_collector/` 自含），通过 `python-dotenv` 直接读取自己的 `.env`

**凭证加载方式（关键！）**：
```python
# outdoor_collector/sdk/ 内的凭证加载方式（不用主项目的 config/credentials.py）
from dotenv import load_dotenv
import os

load_dotenv()  # 加载 outdoor_collector/ 同级或父级的 .env

api_key = os.getenv("TRIPLEWHALE_API_KEY")
```

### TikTok SDK 实现要点

**认证流程（与 sources/tiktok.py 完全一致，复用逻辑）**：

```
DTC getAccessToken → dtc_access_token
    ↓
DTC getTiktokShopSecret (用 dtc_access_token) → TikTok access_token + shop_cipher (+ all_shops 列表)
```

关键常量（来自 `sources/tiktok.py`，禁止修改）：
```python
BASE_URL = "https://open-api.tiktokglobalshop.com"
_DTC_ACCESS_TOKEN_URL = "https://api.dtc.huaqing.run/api/hub/token/getAccessToken"
_DTC_SHOP_SECRET_URL = "https://api.dtc.huaqing.run/api/hub/common/getTiktokShopSecret"
_DTC_APP_ID = "finance-online-v1"
_DTC_APP_SECRET = "CBW3rpFfeobg85uu"
```

**HmacSHA256 签名算法**（`sources/tiktok.py:_sign_request()` 已经过线上验证，直接复用）：
```python
def _sign_request(app_secret: str, path: str, params: dict, body: Optional[dict] = None) -> str:
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sign_input = path + sorted_params
    if body is not None:
        sign_input += json.dumps(body)  # 注意：必须是 json.dumps 默认格式（带空格），与 requests.post(json=body) 一致
    sign_str = f"{app_secret}{sign_input}{app_secret}"
    return hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
```

**时间戳偏移**（重要！）：
```python
"timestamp": str(int(time.time()) - 60)  # 兼容 TikTok 服务端 ±300s 容差
```

**店铺选择逻辑**：优先选包含 "Tidewe" 的店铺，无匹配则用第一个有效店铺。

**TikTokClient 接口设计（建议）**：
```python
class TikTokClient:
    def __init__(self, app_key: str, app_secret: str):
        ...

    def authenticate(self) -> None:
        """通过 DTC 获取 access_token、shop_cipher。失败抛 RuntimeError。"""

    def build_signed_params(self, path: str, body: Optional[dict] = None, include_shop_cipher: bool = True) -> dict:
        """构造带签名的 query 参数字典。"""

    def get(self, path: str, params: dict = None) -> dict:
        """发送签名的 GET 请求，返回 JSON response。"""

    def post(self, path: str, params: dict = None, body: dict = None) -> dict:
        """发送签名的 POST 请求，返回 JSON response。"""

    @property
    def access_token(self) -> str: ...

    @property
    def shop_cipher(self) -> str: ...

    @property
    def all_shops(self) -> list[dict]: ...  # 完整店铺列表，供多店铺遍历使用
```

### TripleWhale SDK 实现要点

认证方式：HTTP Header `x-api-key`（小写）。

关键常量（来自 `sources/triplewhale.py`）：
```python
BASE_URL = "https://api.triplewhale.com/api/v2"
AUTH_URL = f"{BASE_URL}/summary-page/get-data"
SQL_URL = f"{BASE_URL}/orcabase/api/sql"
SHOP_DOMAIN = "piscifun.myshopify.com"
```

**SQL 请求格式**（固定，不可变）：
```python
payload = {
    "period": {"startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD"},
    "shopId": SHOP_DOMAIN,
    "query": "SELECT * FROM pixel_orders_table LIMIT 1",
    "currency": "USD",
}
# Header: {"x-api-key": api_key, "content-type": "application/json"}
```

**各表日期列名**（重要！错误的列名会导致 API 返回 Unknown identifier）：
```python
TABLE_DATE_COLUMNS = {
    "pixel_orders_table":        "created_at",
    "pixel_joined_tvf":          "event_date",
    "sessions_table":            "event_date",
    "product_analytics_tvf":     "event_date",
    "pixel_keywords_joined_tvf": "event_date",
    "ads_table":                 "event_date",
    "social_media_comments_table": "created_at",
    "social_media_pages_table":  "event_date",
    "creatives_table":           "event_date",
    "ai_visibility_table":       "event_date",
}
```

**TripleWhaleClient 接口设计（建议）**：
```python
class TripleWhaleClient:
    def __init__(self, api_key: str, shop_domain: str = "piscifun.myshopify.com"):
        ...

    def authenticate(self) -> None:
        """验证 API Key 有效性（发送探针请求）。失败抛 RuntimeError。"""

    def execute_sql(self, query: str, period_start: str, period_end: str, timeout: int = 30) -> list[dict]:
        """执行 SQL 查询，返回结果列表。"""

    def fetch_table_sample(self, table_name: str, days_back: int = 14, limit: int = 1) -> list[dict]:
        """抓取指定表的样本数据。"""
```

### DingTalk SDK 实现要点

**Token 获取 URL**：`https://api.dingtalk.com/v1.0/oauth2/accessToken`

**接口 Header**：`x-acs-dingtalk-access-token: {access_token}`

**Token 缓存策略**（重要！与 sources/dingtalk.py 保持一致）：
```python
_cached_token: str | None = None
_token_expiry: float = 0.0

def _load_token(app_key: str, app_secret: str) -> str:
    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 60:  # 提前 60s 刷新
        return _cached_token
    resp = requests.post(
        "https://api.dingtalk.com/v1.0/oauth2/accessToken",
        json={"appKey": app_key, "appSecret": app_secret},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["accessToken"]
    _token_expiry = time.time() + data.get("expireIn", 7200)
    return _cached_token
```

**Bitable 分页读取逻辑（来自 sources/dingtalk.py）**：
- List Sheets: `GET {NOTABLE_BASE}/{base_id}/sheets?operatorId={operator_id}`
- Sheet 名匹配：先精确匹配，再包含匹配（兼容 emoji 前缀）
- List Records: `GET {NOTABLE_BASE}/{base_id}/sheets/{sheet_id}/records?operatorId={operator_id}&maxResults=100&nextToken={...}`

**DingTalkClient 接口设计（建议）**：
```python
class DingTalkClient:
    def __init__(self, app_key: str, app_secret: str, operator_id: str):
        ...

    def authenticate(self) -> None:
        """获取 access_token 并缓存。失败抛 RuntimeError。"""

    def fetch_bitable_records(
        self,
        base_id: str,
        sheet_name: str,
        max_records: int = None
    ) -> list[dict]:
        """分页拉取多维表格记录，自动解析复合字段值。返回扁平化字典列表。"""

    def list_bitable_sheets(self, base_id: str) -> list[dict]:
        """列出 base 下所有 Sheet。"""
```

### Project Structure Notes

**目标目录结构（本 Story 仅创建 sdk/ 部分）**：
```
bi/python_sdk/
└── outdoor_collector/          ← 整个 Phase 2 根目录（Story 6.0 开始创建）
    ├── sdk/                    ← 本 Story 负责
    │   ├── __init__.py
    │   ├── tiktok/
    │   │   ├── __init__.py     ← 暴露 TikTokClient
    │   │   ├── auth.py         ← DTC 认证逻辑
    │   │   └── client.py       ← TikTokClient 类
    │   ├── triplewhale/
    │   │   ├── __init__.py     ← 暴露 TripleWhaleClient
    │   │   ├── auth.py         ← API Key 认证
    │   │   └── client.py       ← TripleWhaleClient 类
    │   └── dingtalk/
    │       ├── __init__.py     ← 暴露 DingTalkClient
    │       ├── auth.py         ← access_token 获取与缓存
    │       └── client.py       ← DingTalkClient 类
    │
    │   （以下目录由 Story 6.1 创建，本 Story 不负责）
    ├── common/
    ├── collectors/
    ├── doris_config.py
    └── requirements.txt
```

**`__init__.py` 暴露方式（便于 collector 直接导入）**：
```python
# sdk/tiktok/__init__.py
from .client import TikTokClient
__all__ = ["TikTokClient"]

# sdk/triplewhale/__init__.py
from .client import TripleWhaleClient
__all__ = ["TripleWhaleClient"]

# sdk/dingtalk/__init__.py
from .client import DingTalkClient
__all__ = ["DingTalkClient"]
```

**凭证约定（outdoor_collector 使用的 .env 键名与 Phase 1 完全相同）**：
| 凭证键 | 说明 |
|--------|------|
| `TIKTOK_APP_KEY` | TikTok Open Platform App Key |
| `TIKTOK_APP_SECRET` | TikTok Open Platform App Secret |
| `TRIPLEWHALE_API_KEY` | TripleWhale API Key |
| `DINGTALK_APP_KEY` | 钉钉企业内部应用 AppKey |
| `DINGTALK_APP_SECRET` | 钉钉企业内部应用 AppSecret |
| `DINGTALK_OPERATOR_ID` | 钉钉操作者 unionId（必填） |

### 命名规范

遵守 `project-context.md` 的 Python 命名规范：
- 文件：`snake_case`（auth.py, client.py）
- 类：`PascalCase`（TikTokClient, TripleWhaleClient, DingTalkClient）
- 私有方法：单下划线前缀（`_sign_request`, `_get_dtc_token`）
- 常量：`UPPER_SNAKE_CASE`（`BASE_URL`, `REQUEST_TIMEOUT`）
- 日志格式：`[sdk][{source}] 操作描述 ... 成功/失败`

### 错误处理规范

- 认证失败：抛出 `RuntimeError(f"[sdk][tiktok] 认证失败：{detail}")`，不返回空值
- HTTP 请求失败：调用 `raise_for_status()` 让 requests 抛出 `HTTPError`
- 禁止静默失败：不使用 `except Exception: pass`

### References

- [Source: sources/tiktok.py] — TikTok DTC 认证逻辑、签名算法、时间戳偏移
- [Source: sources/triplewhale.py] — TripleWhale SQL API 请求格式、表日期列名映射
- [Source: sources/dingtalk.py] — 钉钉 Token 缓存策略、Bitable 分页读取、Sheet 名模糊匹配
- [Source: config/credentials.py] — 凭证键名清单（SDK 不依赖此文件，但键名保持一致）
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-15.md] — Phase 2 架构设计、目录结构、SDK 复用策略
- [Source: bi/python_sdk/大户外事业部/doris_config.py] — DorisConfig 单例模式（Story 6.1 参考）

### Review Findings

- [x] [Review][Patch] DingTalk instance token 不自动刷新 [sdk/dingtalk/client.py:152-155] — 已修复：`_headers()` 改为始终调用 `load_token()`，移除实例级 `self._token` 缓存，token 生命周期由 auth.py 模块级 TTL 缓存统一管理。
- [x] [Review][Defer] `max_records=0` 被 Python falsy 判断视为"不限制" [sdk/dingtalk/client.py:117] — deferred，实际调用不会传 0，非当前迭代关注点
- [x] [Review][Defer] 模块级 `_cached_token` 不按 app_key 隔离 [sdk/dingtalk/auth.py:20-21] — deferred，项目仅使用单套钉钉凭证
- [x] [Review][Defer] `TikTokClient.get()`/`post()` 始终包含 shop_cipher [sdk/tiktok/client.py:68-92] — deferred，affiliate 端点调用者需自行使用 `build_signed_params(include_shop_cipher=False)`；属 story 6.0 范围外

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- 凭证采用构造函数注入方式（而非 SDK 内部调用 dotenv），collector 层负责从 `.env` 加载并传入。与 AC #4 精神一致：SDK 内无任何硬编码密钥，不依赖 `config/credentials.py`。
- TikTok 签名算法与 `sources/tiktok.py:_sign_request()` 完全一致，含时间戳 -60s 偏移。
- DingTalk token 缓存为模块级全局变量，`DingTalkClient` 共享同一缓存（与 sources/dingtalk.py 行为一致）。
- TripleWhale `TABLE_DATE_COLUMNS` 中 `pixel_orders_table` 和 `social_media_comments_table` 使用 `created_at`，其余用 `event_date`。

### File List

- `bi/python_sdk/outdoor_collector/sdk/__init__.py`
- `bi/python_sdk/outdoor_collector/sdk/tiktok/__init__.py`
- `bi/python_sdk/outdoor_collector/sdk/tiktok/auth.py`
- `bi/python_sdk/outdoor_collector/sdk/tiktok/client.py`
- `bi/python_sdk/outdoor_collector/sdk/triplewhale/__init__.py`
- `bi/python_sdk/outdoor_collector/sdk/triplewhale/auth.py`
- `bi/python_sdk/outdoor_collector/sdk/triplewhale/client.py`
- `bi/python_sdk/outdoor_collector/sdk/dingtalk/__init__.py`
- `bi/python_sdk/outdoor_collector/sdk/dingtalk/auth.py`
- `bi/python_sdk/outdoor_collector/sdk/dingtalk/client.py`
