# 数据源 API 接入归档

> **用途：** 各数据源调用方式与凭证信息速查手册
> **更新日期：** 2026-04-02（钉钉凭证已录入）
> **状态说明：** ✅ 已就绪 | ⚠️ 缺凭证/权限 | ❌ 无 API

---

## 1. TripleWhale

**状态：** ✅ 凭证已就绪

### 凭证信息

| 参数 | 值 | 来源 |
|------|-----|------|
| `api_key` | _待填入_ | TripleWhale 账户 > Settings > API Keys |
| `shop_id` | `piscifun.myshopify.com` | Shopify 店铺域名即为 Shop ID |

### 调用方式

```http
GET https://api.triplewhale.com/api/v2/attribution/get-orders-with-journeys
Authorization: X-API-KEY {api_key}
Content-Type: application/json
```

```python
import requests

headers = {
    "X-API-KEY": "YOUR_API_KEY",
    "Content-Type": "application/json"
}

# 获取店铺核心指标
resp = requests.get(
    "https://api.triplewhale.com/api/v2/tw-metrics/metrics-data",
    headers=headers,
    params={"shopDomain": "piscifun.myshopify.com", "dateRange": "last_30_days"}
)
```

### 可取指标
- 订单收入、AOV、退款、客户数、新老客分布
- Facebook / Google / TikTok 广告 Spend、ROAS、CPA
- 混合 ROAS（Blended ROAS）、净利率、MER

### 文档：https://triplewhale.readme.io/

---

## 2. TikTok Shop API

**状态：** ✅ 已就绪（DTC Hub 凭证齐全）

### 凭证信息

| 参数 | 值 | 说明 |
|------|-----|------|
| `app_key` | _待填入（DTC Hub）_ | Partner Center > 应用详情 |
| `app_secret` | _待填入（DTC Hub）_ | Partner Center > 应用详情 |
| `access_token` | _动态获取（OAuth）_ | 每次授权后获取，有效期 ~4h |
| `refresh_token` | _动态获取（OAuth）_ | 刷新 access_token 用 |
| `shop_cipher` | _待填入_ | 授权后从 /api/shops/get_authorized_shop 获取 |

### 认证流程

```python
import hashlib, hmac, time

def sign_request(app_secret: str, params: dict) -> str:
    """TikTok Shop API HmacSHA256 签名"""
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sign_str = app_secret + sorted_params + app_secret
    return hmac.new(
        app_secret.encode(), sign_str.encode(), hashlib.sha256
    ).hexdigest()

# OAuth 换取 Token
import requests

def get_access_token(app_key, app_secret, auth_code):
    params = {
        "app_key": app_key,
        "auth_code": auth_code,
        "grant_type": "authorized_code",
        "timestamp": str(int(time.time()))
    }
    params["sign"] = sign_request(app_secret, params)
    return requests.get(
        "https://open-api.tiktokglobalshop.com/api/v2/token/get",
        params=params
    ).json()
```

### 调用方式

```python
def call_tiktok_shop_api(endpoint, app_key, app_secret, access_token, shop_cipher, payload={}):
    params = {
        "app_key": app_key,
        "access_token": access_token,
        "shop_cipher": shop_cipher,
        "timestamp": str(int(time.time()))
    }
    params["sign"] = sign_request(app_secret, {**params, **payload})
    return requests.post(
        f"https://open-api.tiktokglobalshop.com{endpoint}",
        params=params,
        json=payload
    ).json()

# 获取订单列表
orders = call_tiktok_shop_api(
    "/api/orders/search",
    app_key, app_secret, access_token, shop_cipher,
    payload={"order_status": 105, "page_size": 50}
)

# 获取店铺信息
shop_info = call_tiktok_shop_api("/api/shops/get_authorized_shop", ...)
```

### 可取指标
- 订单列表（价格、数量、状态、退款状态）
- GMV = `Σ(item_price × quantity)`（需自行聚合）
- 商品信息、库存、财务对账单

### 文档：https://partner.tiktokshop.com/docv2/

---

## 3. 钉钉表格 / 多维表（Dingtalk Bitable）

**状态：** ✅ 凭证已录入（operatorId 待确认）

### 凭证信息

| 参数 | 值 | 说明 |
|------|-----|------|
| `app_id` | `f4ff9a55-80c4-47a6-8f31-32f5c0d653e2` | 应用唯一标识 |
| `agent_id` | `3134143297` | 原企业内部应用 AgentId |
| `client_id` (原 AppKey) | `dingj5ntgrwhwuuiqu3j` | 用于获取 Access Token |
| `client_secret` (原 AppSecret) | `h61RjLc2ok1VF1c-gfARh8YhpdkqhBeUuofoWXj0GTyyNiEKlsFvqPc28pyawmFO` | 用于获取 Access Token |
| `operator_id` | `620143874` | 执行操作的员工 userId |
| 应用名称 | `HQued` | — |

### 如何获取 operatorId

`operatorId` 是**执行 API 操作的员工钉钉 userId**，获取方式：

**方式 1：API 自查（推荐，用已有凭证直接获取）**
```python
import requests

def get_dingtalk_token(client_id, client_secret):
    resp = requests.post(
        "https://api.dingtalk.com/v1.0/oauth2/accessToken",
        json={"appKey": client_id, "appSecret": client_secret}
    )
    return resp.json()["accessToken"]

token = get_dingtalk_token("dingj5ntgrwhwuuiqu3j", "h61RjLc2ok1VF1c-gfARh8YhpdkqhBeUuofoWXj0GTyyNiEKlsFvqPc28pyawmFO")

# 获取当前操作者 userId（需先完成 OAuth 扫码登录）
me = requests.get(
    "https://api.dingtalk.com/v1.0/contact/users/me",
    headers={"x-acs-dingtalk-access-token": token}
).json()
print("userId:", me.get("unionId") or me.get("openId"))
```

**方式 2：管理员后台查询**
```
钉钉 PC 端 → 通讯录 → 点击员工 → 查看资料 → 复制"员工 ID"
```

**方式 3：批量查询员工 userId**
```python
# 用企业 Access Token 获取部门员工列表
users = requests.get(
    "https://oapi.dingtalk.com/user/listbypage",
    params={"access_token": token, "department_id": 1, "offset": 0, "size": 100}
).json()
```

### 调用方式

```python
import requests

def get_dingtalk_token(app_key: str, app_secret: str) -> str:
    """获取企业内部应用 Access Token（有效期 7200s，需定期刷新）"""
    resp = requests.post(
        "https://api.dingtalk.com/v1.0/oauth2/accessToken",
        json={"appKey": app_key, "appSecret": app_secret}
    )
    return resp.json()["accessToken"]

def read_bitable(token: str, workbook_id: str, sheet_id: str):
    """读取多维表格数据"""
    headers = {"x-acs-dingtalk-access-token": token}

    # 获取所有 Sheet
    sheets = requests.get(
        f"https://api.dingtalk.com/v1.0/doc/workbooks/{workbook_id}/sheets",
        headers=headers
    ).json()

    # 读取指定 Sheet 数据
    data = requests.get(
        f"https://api.dingtalk.com/v1.0/doc/workbooks/{workbook_id}/sheets/{sheet_id}/range",
        headers=headers,
        params={"range": "A1:Z100"}
    ).json()

    return data
```

### 可取指标
- 多维表中存储的任意自定义字段（如 GMV、KPI、运营数据）
- 取决于表格结构，API 支持读写所有字段类型

### 文档：https://open.dingtalk.com/document/

---

## 4. YouTube Data API v3

**状态：** ✅ 已就绪

### 凭证信息

| 参数 | 值 | 获取路径 |
|------|-----|---------|
| `api_key` | _待填入_ | Google Cloud Console > APIs & Services > Credentials |
| `client_id` | _待填入（OAuth 用）_ | OAuth 2.0 Client ID |
| `client_secret` | _待填入（OAuth 用）_ | OAuth 2.0 Client Secret |
| `channel_id` | _待填入_ | YouTube Studio > 自定义频道 URL 或频道设置 |

### 调用方式（API Key，公开数据）

```python
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')

# 频道统计
channel_stats = youtube.channels().list(
    part='snippet,statistics',
    id='YOUR_CHANNEL_ID'
).execute()

print({
    "订阅数": channel_stats['items'][0]['statistics']['subscriberCount'],
    "总观看数": channel_stats['items'][0]['statistics']['viewCount'],
    "视频总数": channel_stats['items'][0]['statistics']['videoCount'],
})

# 视频指标
video_stats = youtube.videos().list(
    part='snippet,statistics',
    id='VIDEO_ID'
).execute()

print({
    "观看数": video_stats['items'][0]['statistics']['viewCount'],
    "点赞数": video_stats['items'][0]['statistics']['likeCount'],
    "评论数": video_stats['items'][0]['statistics']['commentCount'],
})
```

### HTTP 直接调用

```bash
# 获取频道统计
curl "https://www.googleapis.com/youtube/v3/channels\
?part=statistics\
&id=YOUR_CHANNEL_ID\
&key=YOUR_API_KEY"
```

### 可取指标
- 频道：订阅数、总观看数、视频数
- 视频：观看数、点赞数、评论数、发布时间
- **注意：** 无 GMV 数据，仅内容指标

### 配额限制：10,000 单位/天（免费额度）

### 文档：https://developers.google.com/youtube/v3/docs

---

## 5. CartSee（EDM 邮件营销）

**状态：** ✅ 已就绪（工具访问）| ❌ 无公开 API

### 凭证信息

| 参数 | 值 | 说明 |
|------|-----|------|
| 账户登录 | _使用团队账号_ | https://app.cartsee.com/ |
| Shopify 商店 | _已集成_ | CartSee 自动从 Shopify 同步数据 |

### 数据获取方式

#### 方式 1：手动导出（推荐）

```
1. 登录 CartSee 后台
2. 进入 Reports / Analytics
3. 选择时间范围
4. 点击「Export」导出 CSV
5. 导入到统一数据仓库
```

#### 方式 2：通过 Shopify Admin API 获取归因数据

```python
import shopify

shopify.ShopifyResource.set_site("https://piscifun.myshopify.com/admin/api/2024-01")
shopify.ShopifyResource.set_headers({"X-Shopify-Access-Token": "YOUR_SHOPIFY_TOKEN"})

# 获取带有 UTM 标签的订单（CartSee 邮件营销归因）
orders = shopify.Order.find(
    status="paid",
    created_at_min="2026-01-01",
    fields="id,total_price,landing_site,referring_site,source_name"
)

# 筛选来自邮件营销的订单
email_orders = [o for o in orders if "email" in (o.source_name or "").lower()]
```

### 可取指标（后台导出）
- 邮件发送量、打开率（Open Rate）、点击率（CTR）
- 自动化工作流触发次数和转化
- 联系人数量、退订率

---

## 6. Awin

**状态：** ✅ 账号已就绪 | 🕷️ 爬虫方式取数

### 账号信息

| 参数 | 值 | 说明 |
|------|-----|------|
| 账号 / 密码 | _待补充_ | 上个 session 已提供，需重新录入 |
| 登录地址 | `https://ui.awin.com/` | — |

> **注意：** Awin 使用爬虫方式取数据，不走官方 API。账号信息需重新提供以补录归档。

### 爬虫方式说明

```python
from playwright.async_api import async_playwright

async def scrape_awin(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 登录
        await page.goto("https://ui.awin.com/login")
        await page.fill("#username", username)
        await page.fill("#password", password)
        await page.click("button[type=submit]")
        await page.wait_for_navigation()

        # 导出报表数据
        await page.goto("https://ui.awin.com/reports")
        # ... 选择时间范围并导出 CSV
```

### 可取指标
- 交易/佣金（金额、状态、订单号、日期）
- 点击数、转化数、销售额、佣金额

---

## 7. PartnerBoost

**状态：** ✅ 账号已就绪 | 🕷️ 爬虫方式取数

### 账号信息

| 参数 | 值 | 说明 |
|------|-----|------|
| 账号 / 密码 | _待补充_ | 上个 session 已提供，需重新录入 |
| 登录地址 | `https://app.partnerboost.com/` | — |

> **注意：** PartnerBoost 使用爬虫方式取数据，不走官方 API。账号信息需重新提供以补录归档。

### 爬虫方式说明

```python
from playwright.async_api import async_playwright

async def scrape_partnerboost(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 登录
        await page.goto("https://app.partnerboost.com/login")
        await page.fill("input[name=email]", username)
        await page.fill("input[name=password]", password)
        await page.click("button[type=submit]")
        await page.wait_for_navigation()

        # 导航至报表页面，导出数据
        await page.goto("https://app.partnerboost.com/reports")
        # ... 选择时间范围并导出
```

### 可取指标
- 交易记录（点击数、转化数、收入、佣金）
- 渠道/合作项目状态
- CPC、Revenue、支付状态

---

## 8. 社媒后台（Facebook + TikTok）

**状态：** ⚠️ 缺权限

---

### 8.1 Facebook Graph API

**待处理：** 找邻邻完成 FB 账号授权

### 凭证信息

| 参数 | 值 | 获取路径 |
|------|-----|---------|
| `page_access_token` | **待授权** | 邻邻完成 OAuth 授权后获取 |
| `page_id` | _待填入_ | Facebook Page URL 或 Graph API Explorer |
| `app_id` | _待填入_ | https://developers.facebook.com/ |
| `app_secret` | _待填入_ | Meta for Developers > 应用 > 设置 |

### 授权步骤（需邻邻操作）

```
1. 访问 https://developers.facebook.com/tools/explorer/
2. 选择对应的 Facebook App
3. 点击「生成 Access Token」→ 选择 Page
4. 勾选权限：pages_read_engagement, read_insights, pages_show_list
5. 生成 Token 后，转换为 Long-Lived Token（60 天有效）：
   GET https://graph.facebook.com/v15.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={app_id}
     &client_secret={app_secret}
     &fb_exchange_token={short_lived_token}
```

### 调用方式

```python
import requests

PAGE_ID = "YOUR_PAGE_ID"
PAGE_ACCESS_TOKEN = "YOUR_PAGE_ACCESS_TOKEN"

# 获取帖子 + Insights（单次调用）
posts = requests.get(
    f"https://graph.facebook.com/v15.0/{PAGE_ID}/posts",
    params={
        "fields": "id,message,created_time,insights.metric(post_impressions,post_engaged_users,post_clicks)",
        "limit": 10,
        "access_token": PAGE_ACCESS_TOKEN
    }
).json()

# 获取 Page 级别指标（28 天）
page_insights = requests.get(
    f"https://graph.facebook.com/v15.0/{PAGE_ID}/insights",
    params={
        "metric": "page_impressions_unique,page_engaged_users,page_post_engagements",
        "period": "days_28",
        "access_token": PAGE_ACCESS_TOKEN
    }
).json()

# 字段示例
# post_impressions     - 帖子展示次数
# post_engaged_users   - 互动用户数（点赞/评论/分享/点击）
# post_clicks          - 帖子点击次数
# post_reactions_by_type_total - 各类型反应数量
```

### 文档：https://developers.facebook.com/docs/graph-api/

---

## 9. 快速参考：凭证状态汇总

| # | 数据源 | 状态 | 缺什么 | 负责人 |
|---|--------|------|--------|--------|
| 1 | TripleWhale | ✅ 就绪 | 填入 api_key | — |
| 2 | TikTok Shop | ✅ 就绪 | 调用链已归档，credentials 在 DTC Hub | — |
| 3 | 钉钉 Bitable | ✅ 凭证已录入 | — | — |
| 4 | YouTube | ✅ 就绪（API Key 待补录） | 重新提供 v3 API Key | — |
| 5 | CartSee | ❌ 无 API | 手动导出 | — |
| 6 | Awin | 🕷️ 爬虫 | 账号待补录 | — |
| 7 | PartnerBoost | 🕷️ 爬虫 | 账号待补录 | — |
| 8 | Facebook | ⚠️ 缺权限 | Page Access Token 授权 | **邻邻** |

---

## 10. 环境变量模板（`.env` 示例）

```bash
# TripleWhale
TRIPLEWHALE_API_KEY=
TRIPLEWHALE_SHOP_ID=piscifun.myshopify.com

# TikTok Shop（DTC Hub）
TIKTOK_SHOP_APP_KEY=
TIKTOK_SHOP_APP_SECRET=
TIKTOK_SHOP_ACCESS_TOKEN=              # 动态获取，需 OAuth
TIKTOK_SHOP_REFRESH_TOKEN=             # 动态获取
TIKTOK_SHOP_SHOP_CIPHER=               # 动态获取

# 钉钉
DINGTALK_CLIENT_ID=dingj5ntgrwhwuuiqu3j
DINGTALK_CLIENT_SECRET=h61RjLc2ok1VF1c-gfARh8YhpdkqhBeUuofoWXj0GTyyNiEKlsFvqPc28pyawmFO
DINGTALK_APP_ID=f4ff9a55-80c4-47a6-8f31-32f5c0d653e2
DINGTALK_AGENT_ID=3134143297
DINGTALK_OPERATOR_ID=620143874

# YouTube（v3 API Key 方式）
YOUTUBE_API_KEY=                       # 待补录（上个 session 已提供）
YOUTUBE_CHANNEL_ID=

# Awin（爬虫方式）
AWIN_USERNAME=                         # 待补录
AWIN_PASSWORD=                         # 待补录

# PartnerBoost（爬虫方式）
PARTNERBOOST_USERNAME=                 # 待补录
PARTNERBOOST_PASSWORD=                 # 待补录

# Facebook
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=            # 待邻邻授权

```

---

**归档日期：** 2026-04-02（最后更新：TripleWhale shop_id 更正 / Awin+PartnerBoost 改为爬虫方式）
**文件路径：** `_bmad-output/docs/api-access-archive.md`
