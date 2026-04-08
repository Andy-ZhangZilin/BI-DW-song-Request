# 数据源 API 技术研究报告

> **项目：** datasource-verify（指标数据源验证）
> **研究日期：** 2026-04-02
> **研究范围：** 8 个数据源的 API 技术能力、认证方式、数据字段详解

---

## 执行摘要

本报告对项目涉及的 8 个数据源进行了系统性技术调研，重点分析了：
- ✅ API 可用性与官方文档链接
- ✅ 认证机制（API Key / OAuth 2.0）
- ✅ 可获取的业务指标字段（GMV、订单、流量、佣金等）
- ✅ 关键 API 端点与数据结构
- ✅ Rate limits / 数据刷新频率
- ✅ 中国大陆访问限制

**核心发现：**
1. **6 个数据源有公开 API**（TripleWhale、TikTok Shop、钉钉、YouTube、Awin、Facebook）
2. **2 个数据源无公开 API**（CartSee、PartnerBoost 需通过平台界面或第三方集成）
3. 多数使用 **OAuth 2.0** 认证，部分支持 API Key
4. GMV 通常需通过订单数据聚合计算
5. 部分 API 存在中国大陆访问限制（需 VPN）

---

## 1. TripleWhale（电商数据分析平台）

### 基本信息
- **官方文档：** https://triplewhale.readme.io/
- **API 类型：** RESTful API
- **中国大陆访问：** 可能需要 VPN（未明确说明）

### 认证方式
- **API Key** 认证
- 文档路径：`/reference/api-keys`

### 可获取的数据指标

#### 店铺核心指标
| 字段类别 | 具体指标 |
|---------|---------|
| **订单数据** | Order Revenue（订单收入）、AOV（客单价）、Units Sold（销量）、Refunds（退款）、Taxes（税费） |
| **客户指标** | Customer Counts（客户数）、New vs Existing Customer 分类 |
| **广告平台** | Facebook、Google、TikTok、Microsoft、Amazon、Pinterest、Snapchat、Twitter、LinkedIn 等多平台广告数据（Spend、ROAS、CPA、CTR、Impressions） |
| **自定义指标** | Net Profit（净利润）、Blended ROAS（混合广告回报率）、MER（Marketing Efficiency Ratio）、Net Margin（净利率）、NCPA（New Customer Acquisition Cost）、Return Rate（退货率） |
| **其他数据源** | Amazon Sales、Klaviyo Email/SMS Analytics、GA4 Web Analytics、Customer Journey Tracking、Subscription Metrics |

### GMV 计算方式
- **无直接 GMV 端点**
- 需通过 **Order Revenue** 聚合计算：`GMV = Σ(Order Revenue)`
- 可通过 Data Warehouse Export 导出原始订单数据进行计算

### API 端点示例
```http
GET /api/v1/metrics/store-overview
GET /api/v1/metrics/ad-platforms/{platform}
GET /api/v1/warehouse/export
```

### 使用限制
- **Rate Limits：** 文档未明确披露（需联系技术支持）
- **数据刷新频率：** 接近实时（Real-time），底层使用 ClickHouse 数据库
- **历史数据范围：** 依赖于店铺接入时间

---

## 2. TikTok Shop API（抖音小店开放平台）

### 基本信息
- **官方文档：** https://partner.tiktokshop.com/docv2/page/tts-api-concepts-overview
- **API 版本：** Partner API v2（API Version 202309+，旧版 V1 已于 2026 年停止支持）
- **中国大陆访问：** 国际版需 VPN，中国版（抖店）有独立 API

### 认证方式
- **OAuth 2.0** 强制认证
- **请求签名：** 每个请求必须使用 `HmacSHA256` 算法签名
- **凭证要求：**
  - `App Key`（应用密钥）
  - `App Secret`（应用密钥）
  - `Service ID`（服务 ID）
  - `Shop Cipher`（店铺加密标识符）
  - `Access Token` + `Refresh Token`（通过 OAuth 获取）

### 认证流程
1. 在 Partner Center 注册应用
2. 选择业务区域并申请权限 Scopes（如 Shop Authorized Information、Order Information）
3. 创建授权请求 → 用户授权 → 获取 Authorization Code
4. 用 Code 交换 Access Token
5. 所有请求需携带 `access_token` 和 `shop_cipher`

### 可获取的数据指标

#### Partner API v2（运营数据）
| 数据类别 | 字段/指标 |
|---------|---------|
| **订单数据** | Order IDs、Item Prices、Quantities（数量）、Refund Status（退款状态）、Order Status（订单状态）、Buyer Notes、Status History |
| **商品数据** | Product Metadata、Variants、SKUs、Category Mappings（分类映射）|
| **库存数据** | Stock Levels、Reservations、Warehouse References |
| **财务数据** | Payout Details（支付详情）、Fees（手续费）、Adjustments（调整项）、Statements（对账单）|
| **店铺管理** | `merchant_id`、`shop_ids`、`shop_name`、`business_status`、Certifications |

#### Research API（公开市场数据，无需完整授权）
| 字段 | 说明 |
|------|------|
| `shop_name` | 店铺名称 |
| `shop_rating` | 店铺评分 |
| `shop_review_count` | 评价数量 |
| `item_sold_count` | 已售商品数 |
| `shop_id` | 店铺 ID |
| `product_id` | 商品 ID |
| `product_sold_count` | 商品销量 |
| `product_review_count` | 商品评价数 |
| `product_rating` | 商品评分 |

### GMV 计算方式
- **无直接 GMV 端点**
- 计算公式：`GMV = Σ(order_item_price × qty)` 在退款前
- 数据来源：Partner API v2 Orders 端点或 Seller Center 仪表板
- 建议：计算后的 GMV 需与 Seller Center 财务报表进行对账，以纠正退款和费用

### 其他指标计算
- **AOV（客单价）：** `AOV = GMV / Count(orders)`
- **ROAS（广告回报率）：** 需结合 Events API + Marketing API 的广告归因数据

### 关键 API 端点
```http
# 订单查询
GET /api/orders/detail/query
GET /api/orders/list

# 商品管理
GET /api/products/details
GET /api/products/search

# 财务数据
GET /api/finance/statement

# 店铺信息
GET /api/shops/get_authorized_shop
```

### Webhooks 支持
- 支持订单状态变更、库存变化等实时 Webhook 推送
- 建议：结合定时轮询（Polling）+ Webhook 混合方案确保数据一致性

### 使用限制
- **Rate Limits：** 官方未明确公开，建议实现自适应限流、指数退避、幂等性密钥
- **数据刷新频率：** 近实时（Webhook 延迟 < 1 分钟）
- **历史数据范围：** 依赖于店铺授权时间

---

## 3. 钉钉表格 / 多维表（Dingtalk Bitable API）

### 基本信息
- **官方文档：** https://open.dingtalk.com/document/
  - API 总览：https://open.dingtalk.com/document/development/api-overview
  - 多维表格文档：https://open.dingtalk.com/document/development/api-notable-getallsheets
- **API 类型：** RESTful API（钉钉开放平台）
- **中国大陆访问：** ✅ 无限制（国内平台）

### 认证方式
- **Access Token** 认证
- **权限要求：**
  - 需创建**企业内部应用**
  - 获取 `AppKey`（应用 Key）
  - 获取 `AppSecret`（应用密钥）
  - 获取 `operatorId`（操作人 userId，用于权限验证）
- **管理员授权：** 应用需被管理员授予多维表格的数据读写权限

### 认证流程
1. 登录钉钉开发者后台（https://open-dev.dingtalk.com/）
2. 创建企业内部应用
3. 在应用详情中获取 `AppKey` 和 `AppSecret`
4. 配置服务器出站 IP 白名单和回调域名
5. 使用 AppKey + AppSecret 获取 `access_token`（有效期 7200 秒）
6. 所有 API 请求携带 `access_token` 参数

### 可获取的数据指标

#### 多维表格操作
| 功能 | 端点 | 说明 |
|------|------|------|
| 创建表格 | `POST /v1.0/doc/multiDimTables/create` | 创建新多维表 |
| 查询表格数据 | `POST /v1.0/doc/multiDimTables/query` | 查询表格内容 |
| 获取所有数据表 | `GET /api/notable/getAllSheets` | 列出工作簿下所有 Sheet |
| 创建数据表 | `POST /api/createSheet` | 创建新 Sheet |
| 获取 Sheet 数据 | `GET /api/getSheet` | 获取特定 Sheet 的字段定义和数据 |
| 获取单元格范围 | `GET /api/getRange` | 读取指定单元格范围 |

#### 数据字段管理
- **字段类型：** 文本、数字、日期、选项、公式、附件等（未在文档明确列出所有类型）
- **数组数据处理：** 支持数组字段和关联字段
- **公式支持：** API 读取公式计算值和引用值可能有限制（社区反馈）

### Python SDK 示例
```python
from dingtalk import DingTalkClient

client = DingTalkClient(app_key='xxx', app_secret='xxx')
token = client.get_access_token()

# 获取所有表格
sheets = client.get_all_sheets(workbook_id='xxx')

# 读取表格数据
data = client.get_sheet(sheet_id='xxx')
```

### 使用限制
- **Rate Limits：** 未明确披露，建议使用 OpenAPI Explorer 工具进行调试
- **数据刷新频率：** 实时（数据变更即刻可读）
- **历史数据范围：** 无限制（取决于表格创建时间）
- **访问限制：** 部分高级多维表格接口可能需要特殊开发者身份申请

### 注意事项
- 社区反馈表明，部分多维表格 API **未完全开放**或需特殊申请
- 某些公式和复杂字段类型通过 API 读取可能不完整

---

## 4. YouTube Data API v3

### 基本信息
- **官方文档：** https://developers.google.com/youtube/v3/docs
- **API 版本：** v3
- **中国大陆访问：** ⚠️ 需 VPN（Google 服务在中国受限）

### 认证方式
支持两种认证方式：

#### 方式 1：API Key（公开数据访问）
- **用途：** 访问公开数据（视频信息、频道统计、评论等），无需用户登录
- **获取方式：**
  1. 创建 Google Cloud Project
  2. 启用 YouTube Data API v3
  3. 在 Credentials 标签生成 API Key
- **适用场景：** 无需修改用户账号的只读应用

#### 方式 2：OAuth 2.0（用户授权）
- **用途：** 访问私有用户数据或执行写操作（管理用户视频、播放列表等）
- **获取方式：**
  1. 配置 OAuth Consent Screen
  2. 创建 OAuth Client ID
  3. 用户授权后获取 Access Token
- **适用场景：** 需要代表用户操作的应用（如 `tuber` R 包）

### 可获取的数据指标

#### 频道统计（Channels）
| 指标 | 字段名 | 端点 |
|------|--------|------|
| 总观看次数 | `viewCount` | `channels.list?part=statistics` |
| 订阅人数 | `subscriberCount` | 同上 |
| 视频总数 | `videoCount` | 同上 |
| 频道详情 | `snippet`、`status`、`branding` | `channels.list?part=snippet,status` |

#### 视频指标（Videos）
| 指标 | 字段名 | 端点 |
|------|--------|------|
| 观看次数 | `viewCount` | `videos.list?part=statistics` |
| 点赞数 | `likeCount` | 同上 |
| 踩数 | `dislikeCount`（已停止公开） | 同上 |
| 评论数 | `commentCount` | 同上 |
| 视频元数据 | `snippet`（标题、描述、标签、分类、发布时间等） | `videos.list?part=snippet` |

#### 搜索与排序
- **搜索端点：** `search.list`
- **支持参数：** 关键词、频道 ID、时间范围
- **排序方式：** 观看次数、评分、相关性、发布日期

### API 端点示例
```http
# 获取频道统计（MrBeast 示例）
GET https://www.googleapis.com/youtube/v3/channels
  ?part=statistics
  &id=UCX6OQ3DkcsbYNE6H8uQQuVA
  &key=YOUR_API_KEY

# 获取视频详情
GET https://www.googleapis.com/youtube/v3/videos
  ?part=snippet,statistics
  &id=VIDEO_ID
  &key=YOUR_API_KEY

# 搜索视频
GET https://www.googleapis.com/youtube/v3/search
  ?part=snippet
  &q=react+tutorial
  &type=video
  &maxResults=10
  &key=YOUR_API_KEY
```

### Python 示例
```python
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')

# 获取视频详情
response = youtube.videos().list(
    part='snippet,statistics',
    id='VIDEO_ID'
).execute()

print(response['items'][0]['statistics']['viewCount'])
```

### 使用限制
- **配额限制：** 每个 Google Cloud 项目默认 **10,000 单位/天**
- **配额消耗：** 不同参数消耗不同单位（如 `statistics` 比 `snippet` 消耗更多）
- **扩展配额：** 超过 10,000 单位需申请 Quota Extension
- **数据刷新频率：** 近实时（通常 < 1 小时延迟）

---

## 5. CartSee（EDM 邮件营销平台）

### 基本信息
- **平台类型：** Shopify App（EDM 邮件营销插件）
- **官方页面：** https://apps.shopify.com/cartsee
- **中国大陆访问：** ✅ 无限制（Shopify 应用）

### 核心功能
- 跨境电商营销自动化平台
- 邮件营销（EDM）、SMS、Pop-ups
- 个性化、跨渠道用户营销策略
- 弃购挽回、用户分群、自动化工作流

### API 可用性
⚠️ **无公开 API**

- CartSee 是一个 Shopify 应用，**不提供独立的公开 API**
- 数据获取方式：
  1. **Shopify 集成：** 通过 Shopify 后台自动同步店铺数据（订单、客户、商品）
  2. **手动导出：** 在 CartSee 后台导出营销数据报表（CSV / Excel）
  3. **Webhook 通知：** 部分营销事件（如邮件发送、点击、打开率）可能通过 Webhook 推送到外部系统（需在后台配置）
  4. **第三方集成：** 与 CRM、Analytics 工具集成（如 Google Analytics、Facebook Pixel）

### 可获取的数据指标
虽然无 API，但 CartSee 后台可查看以下指标：
- **邮件营销指标：** 发送量、打开率、点击率、退订率、转化率
- **用户分群数据：** Contacts（联系人数量）、细分标签
- **自动化工作流：** 触发次数、转化 GMV
- **Pop-up 数据：** 展示次数、转化率

### 数据导出方式
```bash
# 方式 1：手动导出（推荐）
1. 登录 CartSee 后台
2. 进入 Reports / Analytics 页面
3. 选择时间范围和指标
4. 导出 CSV / Excel 文件

# 方式 2：Shopify 数据同步
- CartSee 自动从 Shopify 同步订单/客户数据
- 可通过 Shopify Admin API 间接获取关联数据

# 方式 3：爬虫（不推荐，违反 ToS）
- 技术上可通过 Selenium 自动化登录后台抓取数据
- 风险：违反服务条款、账号封禁
```

### 替代方案
如果必须通过 API 获取数据：
- **使用 Shopify Admin API：** 获取订单、客户数据（CartSee 同步的源数据）
- **联系 CartSee 技术支持：** 询问是否提供企业级 API 或数据导出服务
- **使用 Zapier / Make.com：** 通过无代码集成平台连接 CartSee 和其他工具

---

## 6. Awin Publisher API（联盟营销平台）

### 基本信息
- **官方文档：** https://help.awin.com/apidocs/introduction-1
- **API 类型：** RESTful API
- **中国大陆访问：** ✅ 无限制

### 认证方式
- **OAuth 2.0** 认证
- **凭证获取：**
  1. 登录 Awin 账户
  2. 点击右上角用户名 → API Credentials
  3. 或直接访问：https://ui.awin.com/awin-api
  4. 生成 `application_key` 和 `user_api_key`
- **Conversion API 使用 API Key：** 通过 `x-api-key` Header 认证

### 可获取的数据指标

#### Publisher API（发布者数据拉取）
| 数据类别 | 字段/指标 | 说明 |
|---------|---------|------|
| **合作项目** | Programs List、Commission Structures、Program Status | 可推广的广告主列表及佣金结构 |
| **交易数据** | Transactions、Commission Status（Pending/Approved）、Commission Amount | 订单交易记录及佣金状态 |
| **交易明细** | Transaction Parts、Commission Group ID、Amount per Group | 按佣金组拆分的交易明细 |
| **点击数据** | Click Time、Click ID（AWC）、Publisher ID | 点击归因信息 |
| **聚合报表** | Aggregated Reports（按时间/产品/设备维度） | 汇总的点击、销售、佣金数据 |

#### Conversion API（广告主转化上报，双向相关）
| 字段 | 说明 |
|------|------|
| `orderReference` | 订单编号（最大 50 字符） |
| `amount` | 订单金额 |
| `currency` | 货币类型（如 EUR、GBP） |
| `awc` | Awin Click ID（归因参数，附加在落地页 URL） |
| `publisherId` | 发布者 ID |
| `clickTime` | 点击时间戳（Unix timestamp，10 位） |
| `commissionGroups` | 佣金组（如 `DEFAULT`、自定义组） |
| `customerAcquisition` | 客户类型（NEW / EXISTING） |
| `voucher` | 优惠券代码 |
| `linkId` | 推广链接 ID |
| `clickRef` | 自定义点击引用 |

### 归因机制
- **AWC 参数：** Awin Click ID，附加在落地页 URL（如 `?awc=1001_xxx_xxx`）
- **Cookie 长度：** 归因窗口由广告主配置（如 30 天、90 天）
- **备用归因：** 如无 `awc`，可用 `publisherId` + `clickTime` 组合归因
- **Channel 参数：** 必须设置为 `"aw"`，用于去重和防止多渠道重复计佣
- **事件延迟：** 转化事件最多 3 分钟后出现在 Awin 平台

### 关键 API 端点
```http
# Publisher API - 获取交易列表
GET /publishers/{publisherId}/transactions
Authorization: Bearer {oauth_token}

# Conversion API - 上报转化
POST /conversion-api/v1/conversions
x-api-key: {api_key}
Content-Type: application/json

{
  "orders": [
    {
      "orderReference": "#1100011",
      "amount": 111.00,
      "channel": "aw",
      "currency": "GBP",
      "awc": "1001_xxx_xxx",
      "customerAcquisition": "NEW",
      "clickRef": "my_ref",
      "commissionGroups": [
        {
          "code": "DEFAULT",
          "amount": 111.00
        }
      ]
    }
  ]
}
```

### 产品级别追踪
支持详细的产品数据上报（Product Level Tracking）：
- `productId`、`name`、`price`、`quantity`、`sku`、`category`
- 用于细粒度的产品表现分析

### 使用限制
- **Rate Limits：** 未明确披露（建议遵循 RESTful 最佳实践，避免短时间大量请求）
- **批处理：** Conversion API 单次批处理最多 **1000 个订单**
- **数据刷新频率：** 近实时（交易数据通常 < 1 小时同步）
- **历史数据范围：** 可回溯至账户创建时间

---

## 7. PartnerBoost API（联盟合作伙伴平台）

### 基本信息
- **官方网站：** https://www.partnerboost.com/
- **平台类型：** 全链路联盟营销管理平台（Affiliate + Influencer + Brand Ambassador）
- **中国大陆访问：** ✅ 无限制

### API 可用性
⚠️ **有限的公开 API**

- PartnerBoost **不提供完整的公开 REST API 文档**
- 数据获取方式：
  1. **Transaction API：** 通过 `Tools > API > Transaction API` 获取 Channel ID 和 Token
  2. **第三方集成：** 通过 Strackr、Affluent、WeCanTrack、Affiliate.com 等工具间接访问数据
  3. **Webhook 通知：** 支持实时转化通知（需在后台配置）
  4. **手动导出：** 后台 Dashboard 导出报表（CSV / Excel）

### 第三方集成凭证
| 集成平台 | 所需凭证 | 获取路径 |
|---------|---------|---------|
| **Strackr** | Channel ID + Token | `Tools > API > Transaction API` |
| **Affluent** | Brand ID + API Token + API Secret Key | PartnerBoost API Docs 部分 |
| **WeCanTrack** | API Key + Publisher IDs | 后台 API Credentials |
| **Affiliate.com** | PartnerBoost ID + Merchant IDs | 账户设置 |

### 可获取的数据指标
通过 Transaction API 和第三方集成可获取以下数据：

| 数据类别 | 字段/指标 | 说明 |
|---------|---------|------|
| **交易数据** | Transactions、Orders、Conversions | 订单和转化记录 |
| **点击数据** | Clicks、Click-through Rate | 点击量和点击率 |
| **收入数据** | Revenue、Commission、CPC（Cost Per Click） | 收入、佣金、单次点击成本 |
| **合作伙伴** | Channels、Programs、Deals | 渠道列表、合作项目、交易状态 |
| **归因数据** | `uid`（对应 `subid`） | 子 ID 追踪（来自 66,000+ 广告主） |
| **Payments** | Payout Status、Settlement Date | 支付状态和结算日期 |

### 平台功能（非直接 API 访问）
- **自动化工作流：** 自动化合作伙伴入职、佣金计算、支付
- **Influencer Gifting：** 产品赠送管理、内容追踪、支付自动化
- **多点触控归因：** 跨设备/跨渠道客户旅程追踪
- **Shopify 集成：** 自动同步产品信息到 Creatives 库
- **Link Builder：** 自定义追踪链接生成工具
- **App Tracking：** iOS/Android 应用内转化追踪（2023 年 11 月上线）

### API 端点示例（通过第三方）
```http
# Strackr 示例（非官方，通过 Strackr API）
GET /api/partnerboost/transactions
  ?channel_id={CHANNEL_ID}
  &token={TOKEN}
  &start_date=2026-01-01
  &end_date=2026-04-01

# 响应数据（示例）
{
  "transactions": [
    {
      "transaction_id": "TX123456",
      "uid": "subid_789",
      "clicks": 150,
      "conversions": 5,
      "revenue": 1250.00,
      "commission": 125.00
    }
  ]
}
```

### 使用限制
- **Rate Limits：** 未披露（依赖第三方集成工具的限制）
- **数据刷新频率：** 实时（Webhook）或近实时（API 轮询，通常 < 1 小时）
- **历史数据范围：** 依赖账户创建时间

### 注意事项
- **Partnerize ≠ PartnerBoost：** 搜索结果中出现的 Partnerize 是另一个独立的联盟网络，API 架构不同
- **推荐集成方式：** 优先使用 Strackr / Affluent / WeCanTrack 等第三方工具，而非直接调用 PartnerBoost API

---

## 8. Facebook Business Suite 爬虫 + TikTok Business API（社媒广告/内容数据）

### 8.1 Facebook Business Suite（Playwright 爬虫）

> **⚠️ 方案变更（2026-04-08）：** 原计划使用 Facebook Graph API，但受制于国内访问限制和 API 申请流程复杂，改为通过 **Playwright 爬虫**抓取 Meta Business Suite 后台数据。

#### 基本信息
- **目标后台：** Meta Business Suite（`https://business.facebook.com`）
- **登录入口：** `https://business.facebook.com/business/loginpage`
- **登录方式：** 点击"使用 Facebook 登录"按钮 → 输入 Facebook 账号密码
- **目标页面：** 帖子和 Reels 列表（`/latest/posts/published_posts`）
- **凭证类型：** Facebook 账号密码（`FACEBOOK_USERNAME` / `FACEBOOK_PASSWORD`）

#### 目标数据页面

**URL 示例：**
`https://business.facebook.com/latest/posts/published_posts?business_id={business_id}&asset_id={asset_id}&should_show_nux=false`

**可抓取字段（列表第一条记录）：**
| 字段名 | 说明 |
|--------|------|
| 标题 | 帖子文字内容（截断显示） |
| 发布日期 | 帖子发布时间（如 4月7日 21:30） |
| 状态 | 发布状态（已发布/草稿等） |
| 覆盖人数 | 看到帖子的唯一用户数（Reach） |
| 获赞数和心情数 | 点赞 + 其他表情反应总数 |
| 评论数 | 帖子评论数量 |
| 分享次数 | 帖子被分享次数 |

#### 爬虫实现要点
- **工具：** `sync_playwright`，headless Chromium
- **登录流程：**
  1. 打开 `https://business.facebook.com/business/loginpage`
  2. 点击"使用 Facebook 登录"按钮（跳转至 Facebook 账号登录页）
  3. 填入 `FACEBOOK_USERNAME`（邮箱/手机）和 `FACEBOOK_PASSWORD`
  4. 等待跳转回 Business Suite 首页（成功标志：URL 包含 `business.facebook.com/latest`）
- **数据抓取：** 导航至帖子和 Reels 页面，抓取列表中第一条记录的所有可见字段
- **超时设置：** 页面等待 20s，整体执行 90s 内完成

#### 使用限制
- **无 Rate Limit：** 爬虫方式无 API 速率限制，但需控制请求频率避免触发反爬
- **验证码风险：** 若频繁登录可能触发人机验证，遇到时中断并提示手动操作
- **网络要求：** 需可访问 `facebook.com`（国内需 VPN）

---

### 8.2 TikTok Business API（Marketing API）

#### 基本信息
- **官方文档：** https://business-api.tiktok.com/portal
- **API 类型：** TikTok for Business API（也称 Marketing API）
- **中国大陆访问：** ⚠️ 国际版需 VPN，国内版（抖音）有独立 API

#### 认证方式
- **OAuth 2.0** 强制认证
- **审批流程：**
  1. 在 TikTok for Developers 注册开发者账号
  2. 创建应用并提交审批（需提供使用场景）
  3. 获得批准后才能访问 API
- **账号要求：** TikTok Business Account（非个人账号）
- **沙盒测试：** 上线前需在沙盒环境测试

#### 可获取的数据指标

##### 广告投放指标
| 指标类别 | 字段/指标 | 说明 |
|---------|---------|------|
| **曝光与点击** | `impressions`、`clicks`、`ctr`（点击率） | 广告展示次数、点击次数、点击率 |
| **花费与成本** | `spend`、`cpc`（Cost Per Click）、`cpm`（Cost Per Mille） | 广告花费、单次点击成本、千次展示成本 |
| **转化数据** | `conversion`、`sales_lead`、`total_sales_lead_value` | 转化次数、销售线索、线索价值 |
| **覆盖与频次** | `reach`、`frequency` | 覆盖人数、广告频次 |

##### 受众洞察
- 按地域、兴趣、性别、设备类型分析受众
- 自定义受众分群（Custom Audiences）
- 相似受众（Lookalike Audiences）

##### 有机内容指标（非广告）
通过以下 API 获取有机内容数据：
- **Mentions API：** 追踪品牌在热门有机视频中的提及
- **Spark Ads Recommendation API：** 识别高表现有机内容，用于 Spark Ads 放大

##### Commercial Content API（公开广告库，竞品分析）
- 广告主公开数据：广告投放日期、定向信息、表现指标
- 用于竞品分析和市场研究

#### 关键 API 端点（示例）
```http
# 获取广告投放报告
GET /open_api/v1.3/reports/integrated/get/
  ?advertiser_id={ADVERTISER_ID}
  &report_type=BASIC
  &data_level=AUCTION_CAMPAIGN
  &dimensions=["campaign_id","stat_time_day"]
  &metrics=["spend","impressions","clicks","conversions"]
  &start_date=2026-01-01
  &end_date=2026-04-01
  &access_token={ACCESS_TOKEN}
```

#### Python SDK 示例
```python
from tiktok_business_api_sdk import TikTokBusinessApiClient

client = TikTokBusinessApiClient(
    access_token='YOUR_ACCESS_TOKEN',
    app_id='YOUR_APP_ID',
    secret='YOUR_APP_SECRET'
)

# 获取广告投放数据
report = client.reports.get_integrated_report(
    advertiser_id='123456',
    report_type='BASIC',
    data_level='AUCTION_ADGROUP',
    dimensions=['adgroup_id', 'stat_time_day'],
    metrics=['spend', 'impressions', 'clicks', 'ctr', 'conversion'],
    start_date='2026-01-01',
    end_date='2026-04-01'
)

print(report.data)
```

#### 使用限制
- **Rate Limits：** 需遵循 TikTok 限流规则（具体限制未公开，需在实现中监控响应头）
- **数据延迟：** Reporting API 约有 **11 小时延迟**
- **归因窗口：** 建议增量同步设置至少 **3 天归因窗口**
- **数据刷新频率：** 每日更新（非实时）

#### 替代方案
如果官方 API 审批困难：
- **SaleSmartly：** 聚合 TikTok 数据、管理 DM、分析仪表板
- **EchoTik：** 预构建的 TikTok 数据集成工具
- **开源库（TikTokApi GitHub）：** 非官方库，合规性风险较高

---

## 9. 数据源能力对比总览

| # | 数据源 | API 可用性 | 认证方式 | GMV 获取方式 | 中国大陆访问 | 数据刷新频率 |
|---|--------|-----------|---------|------------|------------|------------|
| 1 | **TripleWhale** | ✅ 公开 API | API Key | 订单收入聚合 | ⚠️ 可能需 VPN | 近实时 |
| 2 | **TikTok Shop** | ✅ Partner API v2 | OAuth 2.0 + 签名 | 订单价格 × 数量聚合 | ⚠️ 国际版需 VPN | 近实时（Webhook） |
| 3 | **钉钉 Bitable** | ✅ 开放平台 API | Access Token | 读取表格内自定义 GMV 字段 | ✅ 无限制 | 实时 |
| 4 | **YouTube** | ✅ Data API v3 | API Key / OAuth 2.0 | 无 GMV（只有观看/订阅数据） | ⚠️ 需 VPN | 近实时（< 1h） |
| 5 | **CartSee** | ❌ 无公开 API | N/A | 手动导出 / Shopify API 间接 | ✅ 无限制 | 手动 |
| 6 | **Awin** | ✅ Publisher API | OAuth 2.0 | 交易金额（amount）聚合 | ✅ 无限制 | 近实时 |
| 7 | **PartnerBoost** | ⚠️ 有限 API | Token（第三方集成） | 收入（revenue）聚合 | ✅ 无限制 | 近实时 |
| 8 | **Facebook Business Suite** | ❌ 无 API（改用爬虫） | 账号密码登录 | 无 GMV（只有互动/覆盖数据） | ⚠️ 需 VPN | 近实时 |
| 8 | **TikTok Business** | ✅ Marketing API | OAuth 2.0（需审批） | 无 GMV（只有广告花费/转化） | ⚠️ 需 VPN | 约 11h 延迟 |

---

## 10. 关键发现与建议

### 10.1 API 可用性
- **5 个数据源有完整公开 API**（TripleWhale、TikTok Shop、钉钉、YouTube、Awin）
- **3 个数据源无公开 API，改用爬虫：**
  - **CartSee：** Playwright 爬虫，账号密码登录
  - **PartnerBoost：** Playwright 爬虫，账号密码登录
  - **Facebook Business Suite：** Playwright 爬虫，Facebook 账号密码登录（原计划 Graph API，因国内访问限制改为爬虫）

### 10.2 GMV 数据获取
- **TripleWhale、TikTok Shop、Awin、PartnerBoost**：可通过订单/交易数据聚合计算 GMV
- **YouTube、Facebook、TikTok Business**：无 GMV 数据（只提供内容/广告指标）
- **钉钉 Bitable**：可存储和读取自定义 GMV 字段（手动维护或其他系统写入）
- **CartSee**：GMV 需从 Shopify 订单数据中提取（归因到 CartSee 的邮件营销渠道）

### 10.3 认证方式
- **OAuth 2.0 主流**：TikTok Shop、Awin、TikTok Business
- **API Key 简化**：TripleWhale、YouTube（公开数据）、钉钉（Access Token）
- **混合模式**：YouTube 支持 API Key（公开）+ OAuth（私有）

### 10.4 中国大陆访问
- **需 VPN**：TripleWhale（可能）、YouTube、Facebook Business Suite（爬虫）、TikTok Business（国际版）
- **无限制**：钉钉、CartSee、Awin、PartnerBoost
- **替代方案**：TikTok Shop 和 TikTok Business 的中国版（抖店、巨量引擎）有独立 API

### 10.5 数据刷新频率
- **实时/近实时（< 1h）**：TripleWhale、TikTok Shop（Webhook）、钉钉、YouTube、Awin、Facebook Business Suite（爬虫）
- **延迟较大（> 10h）**：TikTok Business API（约 11 小时）
- **手动更新**：CartSee（依赖导出操作）

### 10.6 Rate Limits 风险
- **明确限制**：YouTube（10,000 单位/天）
- **未披露限制**：TripleWhale、TikTok Shop、Awin、PartnerBoost（需实现自适应限流）
- **建议策略**：
  - 实现指数退避（Exponential Backoff）
  - 缓存频繁查询的数据
  - 使用批量请求（Batch Requests）

### 10.7 实施优先级建议

#### 阶段 1：高优先级（凭证已就绪 + 有公开 API）
1. **Awin Publisher API** — 佣金数据，OAuth 2.0，文档完善
2. **YouTube Data API v3** — 频道/视频统计，API Key 即可开始
3. **TripleWhale API** — 电商核心指标，API Key 认证

#### 阶段 2：中优先级（需配置凭证 + 有公开 API）
4. **TikTok Shop API** — OAuth 流程较复杂，需申请 Scopes
5. **钉钉 Bitable API** — 需创建企业内部应用获取凭证
6. **Facebook Business Suite** — 改用 Playwright 爬虫，账号密码已具备

#### 阶段 3：低优先级（无 API 或需第三方工具）
7. **CartSee** — 手动导出或通过 Shopify API 间接获取
8. **PartnerBoost** — 使用 Strackr / Affluent 集成
9. **TikTok Business API** — 需审批流程，数据延迟较大

---

## 11. 下一步行动

### 11.1 立即行动
- [x] **TripleWhale：** 确认 Piscifun 的 shopId（联系 TripleWhale 技术支持）
- [ ] **钉钉 Bitable：** 创建企业内部应用，获取 AppKey / AppSecret / operatorId
- [x] **Facebook Business Suite：** 已具备账号密码凭证，改用 Playwright 爬虫实现（Story 4.5）

### 11.2 技术验证（PoC）
建议按以下顺序进行技术验证：
1. **Awin API** — 文档最完善，快速验证 OAuth 流程
2. **YouTube API** — API Key 方式最简单，立即可测试
3. **TikTok Shop API** — 验证 OAuth + 签名机制
4. **钉钉 API** — 测试企业内部应用权限获取

### 11.3 数据集成架构设计
- **统一认证管理：** 构建 OAuth Token 刷新机制（自动续期）
- **Rate Limit 防护：** 实现分布式限流（Redis + Token Bucket）
- **数据同步策略：**
  - 实时数据：Webhook + 轮询混合
  - 历史数据：批量回填（Batch Backfill）
- **GMV 计算服务：** 统一订单数据聚合逻辑

### 11.4 文档与代码仓库
- 为每个数据源创建独立的集成模块
- 编写单元测试（Mock API 响应）
- 维护 API 变更日志（Changelog）

---

## 12. 参考资料

### 官方文档链接汇总
1. **TripleWhale：** https://triplewhale.readme.io/
2. **TikTok Shop：** https://partner.tiktokshop.com/docv2/page/tts-api-concepts-overview
3. **钉钉开放平台：** https://open.dingtalk.com/document/
4. **YouTube Data API v3：** https://developers.google.com/youtube/v3/docs
5. **Awin Publisher API：** https://help.awin.com/apidocs/introduction-1
6. **Facebook Business Suite（爬虫）：** https://business.facebook.com/business/loginpage
7. **TikTok Business API：** https://business-api.tiktok.com/portal

### 开发者工具
- **TikTok Shop Partner Center：** https://partner.tiktokshop.com/
- **Google Cloud Console：** https://console.cloud.google.com/
- **Meta for Developers：** https://developers.facebook.com/
- **钉钉开发者后台：** https://open-dev.dingtalk.com/
- **Awin API Credentials：** https://ui.awin.com/awin-api

---

**报告完成日期：** 2026-04-02
**研究人员：** Capy（HappyCapy Research Agent）
**版本：** v1.0
