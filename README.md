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
python validate.py --source dingtalk          # 全部 8 张多维表格
python validate.py --source dingtalk_sheet    # 红人支付需求（普通表格）
python validate.py --source youtube
python validate.py --source awin
python validate.py --source cartsee
python validate.py --source partnerboost

# 指定单张钉钉多维表格
python validate.py --source dingtalk --table kol_tidwe_寄样记录
python validate.py --source dingtalk --table outdoor_原始素材生产及优化

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
| 钉钉多维表 | REST API（Notable API） | `DINGTALK_APP_KEY` / `DINGTALK_APP_SECRET` / `DINGTALK_OPERATOR_ID` |
| 钉钉普通表格 | REST API（Workbook API） | `DINGTALK_APP_KEY` / `DINGTALK_APP_SECRET` / `DINGTALK_OPERATOR_ID` |
| YouTube | REST API | `YOUTUBE_API_KEY` |
| Awin | Playwright 爬虫 | `AWIN_USERNAME` / `AWIN_PASSWORD` |
| CartSee | Playwright 爬虫 | `CARTSEE_USERNAME` / `CARTSEE_PASSWORD` |
| PartnerBoost | Playwright 爬虫 | `PARTNERBOOST_USERNAME` / `PARTNERBOOST_PASSWORD` |

### 钉钉多维表格（dingtalk）接入的 Sheet 清单

| source key | 工作簿 | Base ID | Sheet 名称 |
|------------|--------|---------|-----------|
| `kol_tidwe_红人信息汇总` | KOL营销管理总表-TideWe | `Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4` | 红人信息汇总 |
| `kol_tidwe_寄样记录` | KOL营销管理总表-TideWe | `Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4` | 寄样记录 |
| `kol_tidwe_内容上线` | KOL营销管理总表-TideWe | `Gl6Pm2Db8D332mAgCnk7N0AaJxLq0Ee4` | 内容上线 |
| `outdoor_原始素材生产及优化` | 26年新版-大户外一张表3.0 | `Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l` | 原始素材生产及优化 |
| `outdoor_拍摄资源表KOL信息` | 26年新版-大户外一张表3.0 | `Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l` | 拍摄资源表-KOL信息 |
| `outdoor_素材分析表格` | 26年新版-大户外一张表3.0 | `Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l` | 素材分析表格 |
| `outdoor_参数表` | 26年新版-大户外一张表3.0 | `Qnp9zOoBVBZZXzArF0nlpBn0V1DK0g6l` | 参数表\|勿动 |
| `video_成片交付` | 视频组日常工作总表 | `20eMKjyp81RR5NAQC79gy2YEWxAZB1Gv` | 视频组成片交付&数据汇总表 |

### 钉钉普通表格（dingtalk_sheet）接入的工作簿清单

| source | 工作簿名称 | Workbook ID |
|--------|-----------|-------------|
| `dingtalk_sheet` | 红人支付需求 | `XPwkYGxZV3RRlXAQCjaPjk6zWAgozOKL` |

## 运行测试

```bash
pytest
```
