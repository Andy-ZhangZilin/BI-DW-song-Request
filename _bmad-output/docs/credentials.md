# 数据源凭证状态总览

> 项目：datasource-verify（指标数据源验证）
> 更新日期：2026-04-02（修订：2026-04-02）

## 凭证状态

| # | 数据源 | 凭证状态 | 缺什么 / 备注 |
|---|--------|----------|---------------|
| 1 | TripleWhale | ✅ 已就绪 | shopId 已确认：`piscifun.myshopify.com` |
| 2 | TikTok Shop API | ✅ 已就绪 | DTC Hub 凭证齐全，可直接调用 |
| 3 | 钉钉表格 / 多维表 | ✅ 已就绪 | AppKey + AppSecret + operatorId 全部就绪 |
| 4 | YouTube | ✅ 已就绪 | 无缺口 |
| 5 | CartSee (EDM) | ✅ 已就绪 | 有账号密码，采用**爬虫**方案 |
| 6 | Awin | ✅ 已就绪 | 无缺口 |
| 7 | PartnerBoost | ✅ 已就绪 | 有账号密码，采用**爬虫**方案 |
| 8 | 社媒后台 | ⏳ 待接入 | 后续获取账号密码，采用**爬虫**方案 |

## 待办事项

- [x] 确认 TripleWhale — Piscifun 的 shopId 值（`piscifun.myshopify.com`）
- [x] 钉钉：AppKey + AppSecret + operatorId 全部就绪
- [ ] 社媒后台：后续获取账号密码，规划爬虫方案

## 访问方式汇总（含修订）

| # | 数据源 | 访问方式 | 状态 |
|---|--------|---------|------|
| 1 | TripleWhale | REST API（API Key） | ✅ 可立即开发 |
| 2 | TikTok Shop | OAuth 2.0 API | ✅ 可立即开发 |
| 3 | 钉钉 | API（钉钉开放平台） | ✅ 可立即开发 |
| 4 | YouTube | REST API（API Key/OAuth） | ✅ 可立即开发 |
| 5 | CartSee | **爬虫（账号密码）** | ✅ 待实现 |
| 6 | Awin | REST API（OAuth 2.0） | ✅ 可立即开发 |
| 7 | PartnerBoost | **爬虫（账号密码）** | ✅ 待实现 |
| 8 | 社媒后台 | **爬虫（账号密码，待获取）** | ⏳ 后续跟进 |

## 访问方式说明

### 1. TripleWhale

- **访问方式：** API（REST）
- **状态：** ✅ 完全就绪
- **shopId：** `piscifun.myshopify.com`（已确认）

### 2. TikTok Shop API

- **访问方式：** TikTok Shop Open Platform API
- **状态：** DTC Hub 的凭证已齐全，可直接调用
- **可获取数据：** 订单、GMV、商品、流量等

### 3. 钉钉表格 / 多维表

- **访问方式：** 钉钉开放平台 API（企业内部应用）
- **状态：** ✅ 完全就绪
- **已有：**
  - AppKey：✅ 已就绪
  - AppSecret：✅ 已就绪
  - operatorId：✅ `620143874`

### 4. YouTube

- **访问方式：** YouTube Data API v3（Google OAuth 2.0）
- **状态：** 已就绪
- **可获取数据：** 频道统计、视频数据、播放量等

### 5. CartSee (EDM)

- **访问方式：** 爬虫（账号密码登录后台抓取）
- **状态：** ✅ 有账号密码，待实现爬虫
- **数据获取方案：** 浏览器自动化（Selenium/Playwright）登录后台抓取数据

### 6. Awin

- **访问方式：** Awin Publisher API
- **状态：** 已就绪
- **可获取数据：** 联盟推广佣金、点击、转化等

### 7. PartnerBoost

- **访问方式：** 爬虫（账号密码登录后台抓取）
- **状态：** ✅ 有账号密码，待实现爬虫
- **数据获取方案：** 浏览器自动化（Selenium/Playwright）登录后台抓取数据
- **备注：** 若后台数据结构简单，也可尝试直接调用 Transaction API（Channel ID + Token）

### 8. 社媒后台

- **访问方式：** 爬虫（账号密码，待获取）
- **状态：** ⏳ 后续跟进，账号密码获取后实现
- **平台范围：** Facebook、TikTok（内容/互动数据）
- **备注：** YouTube 已有 API 凭证，优先走 YouTube Data API v3，无需爬虫
