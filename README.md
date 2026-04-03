# outdoor-data-validator

本地 CLI 工具，用于验证各外部数据源的 API 接入状态，并自动发现可用字段，生成对标报告。

## 环境要求

- Python 3.10+
- 能访问各数据源 API 的网络环境

## 安装

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器（必须单独执行，无法通过 requirements.txt 自动完成）
playwright install chromium

# 3. 配置凭证
cp .env.example .env
# 编辑 .env，填入各数据源的真实凭证
```

> **注意**：`playwright install chromium` 是独立步骤，会下载 Chromium 浏览器二进制文件（约 100MB），
> 必须在 `pip install` 之后手动执行，否则爬虫数据源（Awin / CartSee / PartnerBoost）无法运行。

## 运行

```bash
# 运行单个数据源验证
python validate.py --source triplewhale
python validate.py --source tiktok
python validate.py --source dingtalk
python validate.py --source youtube
python validate.py --source awin
python validate.py --source cartsee
python validate.py --source partnerboost

# 运行全部数据源验证
python validate.py --all

# 查看帮助
python validate.py --help
```

## 输出

报告生成于 `reports/` 目录：

- `reports/{source}-raw.md`：每次运行自动覆盖，记录最新实际返回字段
- `reports/{source}-validation.md`：首次自动创建模板，后续由人工维护对标结论

## 数据源

| 数据源 | 接入方式 | 凭证键名 |
|--------|---------|---------|
| TripleWhale | REST API | `TRIPLEWHALE_API_KEY` |
| TikTok Shop | REST API + refresh_token 自动换取 | `TIKTOK_REFRESH_TOKEN` / `TIKTOK_APP_KEY` / `TIKTOK_APP_SECRET` |
| 钉钉多维表 | REST API | `DINGTALK_APP_KEY` / `DINGTALK_APP_SECRET` |
| YouTube | REST API | `YOUTUBE_API_KEY` |
| Awin | Playwright 爬虫 | `AWIN_USERNAME` / `AWIN_PASSWORD` |
| CartSee | Playwright 爬虫 | `CARTSEE_USERNAME` / `CARTSEE_PASSWORD` |
| PartnerBoost | Playwright 爬虫 | `PARTNERBOOST_USERNAME` / `PARTNERBOOST_PASSWORD` |

## 运行测试

```bash
pytest
```
