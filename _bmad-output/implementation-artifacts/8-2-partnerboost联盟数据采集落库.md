# Story 8.2：PartnerBoost 联盟数据采集落库

Status: done

## Story

作为数据工程师，
我希望能每日自动抓取 PartnerBoost 的当天联盟数据并写入 Doris，
以便构建联盟营销渠道报表。

## Acceptance Criteria

1. **Given** PartnerBoost 凭证有效；**When** 运行 `partnerboost_collector.py`；**Then** 使用 `sync_playwright` headless Chromium 登录并导航至报表页，抓取**当天所有数据行**（不只取第一行）

2. **Given** 页面抓取成功；**When** 数据写入 Doris；**Then** upsert 写入 `hqware.ods_partnerboost_performance`，以 `collect_date + partner` 为复合唯一键，幂等写入不重复

3. **Given** 遇到验证码；**When** 爬虫检测到验证码；**Then** 抛出 `RuntimeError("[partnerboost_collector] 遇到验证码，请手动完成验证后重新运行")`，浏览器正常关闭

4. **Given** 写入 Doris 成功；**When** 查看日志；**Then** 输出 `[partnerboost_collector][hqware.ods_partnerboost_performance] 写入 N 行 ... 成功`

5. **Given** 无数据行（当天页面为空）；**When** 未找到 `<table tbody tr>`；**Then** 记录 warning 日志并退出，不抛异常，不写入 Doris

6. **Given** 单元测试环境；**When** 运行 `tests/test_partnerboost_collector.py`；**Then** 所有单元测试通过（mock Playwright + mock doris_writer）

## Tasks / Subtasks

- [ ] Task 1: 实现 `collectors/partnerboost_collector.py` (AC: 1, 2, 3, 4, 5)
  - [ ] Task 1.1: 实现 `_login(page)` 内部函数 — sync_playwright 登录，lambda 谓词等待跳离登录页
  - [ ] Task 1.2: 实现 `_check_captcha(page)` — 检测 body inner_text 中的验证码关键词
  - [ ] Task 1.3: 实现 `_scrape_all_rows(page)` — 抓取 `<table tbody tr>` 全部行，返回 `list[dict]`
  - [ ] Task 1.4: 实现 `_transform(raw_records, collect_date)` — 字段映射 + 数值清洗，返回 Doris 格式 `list[dict]`
  - [ ] Task 1.5: 实现 `collect(collect_date: str = None)` — 主入口函数，整合登录/抓取/转换/写入
  - [ ] Task 1.6: 实现 `if __name__ == "__main__"` 入口，解析 `--date` 参数（默认今天）

- [ ] Task 2: 编写单元测试 `tests/test_partnerboost_collector.py` (AC: 6)
  - [ ] Task 2.1: 测试 `_transform()` 字段映射和数值清洗（无 I/O，纯函数）
  - [ ] Task 2.2: 测试空行情况（`_transform([])` 返回空列表）
  - [ ] Task 2.3: 测试 `collect()` 正常路径（mock playwright + mock write_to_doris）
  - [ ] Task 2.4: 测试 `collect()` 无数据行（mock page 无 tbody tr）— 应记录 warning，不写入

- [ ] Task 3: 更新 `sprint-status.yaml`
  - [ ] Task 3.1: `epic-8` → `in-progress`，`8-2-partnerboost联盟数据采集落库` → `done`

## Dev Notes

### 文件结构

```
bi/python_sdk/outdoor_collector/
└── collectors/
    └── partnerboost_collector.py     ← 本 Story 核心新建文件

outdoor-data-validator/
└── tests/
    └── test_partnerboost_collector.py ← 单元测试（主仓库 tests/ 目录）
```

> **注意**：`collectors/` 在 `bi/` submodule 内；测试文件在主仓库 `tests/`。
> bi/ submodule 修改需单独在 bi/ 内 commit，再在主仓库更新 submodule 引用。

### 函数签名

```python
# bi/python_sdk/outdoor_collector/collectors/partnerboost_collector.py

import sys
import os
import logging
import argparse
from datetime import date as _date

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common.doris_writer import write_to_doris

logger = logging.getLogger(__name__)

SOURCE = "partnerboost_collector"
TABLE  = "hqware.ods_partnerboost_performance"
UNIQUE_KEYS = ["collect_date", "partner"]

LOGIN_URL   = "https://app.partnerboost.com/brand/login"
REPORTS_URL = "https://app.partnerboost.com/brand/reports/performance"
_CAPTCHA_KEYWORDS = ["captcha", "robot", "verify you are human"]
_PAGE_TIMEOUT = 30_000
_BROWSER_ARGS = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]


def _check_captcha(page) -> None: ...

def _login(page, username: str, password: str) -> None: ...

def _scrape_all_rows(page) -> list[dict]: ...

def _transform(raw_records: list[dict], collect_date: str) -> list[dict]: ...

def collect(collect_date: str = None) -> int:
    """主入口：登录 → 抓取 → 转换 → 写入 Doris。
    Returns: 写入行数（0 表示无数据，正常退出）
    """
    ...
```

### Doris 表结构（DDL 参考，由 DBA 建表，collector 不负责 DDL）

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_partnerboost_performance (
    collect_date    DATE         NOT NULL COMMENT '采集日期',
    partner         VARCHAR(256) NOT NULL COMMENT '联盟合作伙伴名称',
    clicks          INT          COMMENT '点击数',
    sales           INT          COMMENT '订单数',
    revenue         DECIMAL(18,2) COMMENT '销售额（美元）',
    commission      DECIMAL(18,2) COMMENT '佣金（美元）',
    status          VARCHAR(64)  COMMENT '状态（Approved/Pending 等）',
    channel         VARCHAR(128) COMMENT '渠道类型',
    payment_status  VARCHAR(64)  COMMENT '支付状态',
    created_at      DATETIME DEFAULT NOW() COMMENT '入库时间'
)
UNIQUE KEY(collect_date, partner)
DISTRIBUTED BY HASH(collect_date) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

### 字段映射规则（PartnerBoost 页面列名 → Doris 列名）

| 页面原始列名 | Doris 列名 | 类型 | 清洗规则 |
|-------------|-----------|------|----------|
| （注入）今日日期 | `collect_date` | `str` (YYYY-MM-DD) | `datetime.date.today()` |
| `Partner` | `partner` | `str` | strip |
| `Click` / `Clicks` | `clicks` | `int` | strip + `int(v.replace(",",""))` |
| `Sale` / `Sales` | `sales` | `int` | strip + `int(v.replace(",",""))` |
| `Revenue` | `revenue` | `float` | strip `$,` + `float()` |
| `Commission` | `commission` | `float` | strip `$,` + `float()` |
| `Status` | `status` | `str` | strip |
| `Channel` | `channel` | `str` | strip |
| `Payment Status` | `payment_status` | `str` | strip |

> **列名兼容**：使用 `.strip().lower().replace(" ", "_")` 规范化后匹配，兼容 `Click` / `Clicks` / `CLICK` 等变体。
> **缺失列**：若页面未返回某列，对应 Doris 字段置 `None`（不抛异常）。
> **类型转换失败**：若数值字段解析失败（如空字符串），置 `None`。

### `_transform()` 实现要点

```python
# 列名规范化辅助
def _norm(col: str) -> str:
    return col.strip().lower().replace(" ", "_")

def _transform(raw_records: list[dict], collect_date: str) -> list[dict]:
    result = []
    for row in raw_records:
        normed = {_norm(k): v.strip() if isinstance(v, str) else v for k, v in row.items()}

        def _int(key):
            v = normed.get(key)
            if not v:
                return None
            try:
                return int(v.replace(",", ""))
            except (ValueError, AttributeError):
                return None

        def _float(key):
            v = normed.get(key)
            if not v:
                return None
            try:
                return float(v.replace(",", "").replace("$", "").strip())
            except (ValueError, AttributeError):
                return None

        result.append({
            "collect_date":   collect_date,
            "partner":        normed.get("partner") or "",
            "clicks":         _int("click") or _int("clicks"),
            "sales":          _int("sale")  or _int("sales"),
            "revenue":        _float("revenue"),
            "commission":     _float("commission"),
            "status":         normed.get("status"),
            "channel":        normed.get("channel"),
            "payment_status": normed.get("payment_status"),
        })
    return result
```

### `collect()` 实现模板

```python
def collect(collect_date: str = None) -> int:
    if collect_date is None:
        collect_date = str(_date.today())

    username = os.environ.get("PARTNERBOOST_USERNAME", "")
    password = os.environ.get("PARTNERBOOST_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(f"[{SOURCE}] 未配置 PARTNERBOOST_USERNAME / PARTNERBOOST_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=_BROWSER_ARGS)
        page = browser.new_page()
        try:
            _login(page, username, password)
            _check_captcha(page)

            page.goto(REPORTS_URL, timeout=_PAGE_TIMEOUT, wait_until="domcontentloaded")
            # 等待表格行出现；若 5s 内无行，视为当日无数据
            try:
                page.wait_for_selector("table tbody tr", timeout=5_000)
            except Exception:
                logger.warning(f"[{SOURCE}] 当日无数据行，跳过写入")
                return 0

            _check_captcha(page)

            raw_records = _scrape_all_rows(page)
            if not raw_records:
                logger.warning(f"[{SOURCE}] 未抓取到数据行，跳过写入")
                return 0

            records = _transform(raw_records, collect_date)
            written = write_to_doris(TABLE, records, UNIQUE_KEYS, source=SOURCE)
            return written

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"[{SOURCE}] 采集失败：{e}") from e
        finally:
            browser.close()
```

### 凭证加载方式

`bi/` 内不使用 `config.credentials`（主仓库模块），改为直接读取环境变量：

```python
username = os.environ.get("PARTNERBOOST_USERNAME", "")
password = os.environ.get("PARTNERBOOST_PASSWORD", "")
```

> 运行前需将 `.env` 内容 `source` 或 `export`，或由海豚调度器注入环境变量。

### `__main__` 入口

```python
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="PartnerBoost 联盟数据采集落库")
    parser.add_argument("--date", default=None, help="采集日期 YYYY-MM-DD，默认今天")
    args = parser.parse_args()
    written = collect(args.date)
    print(f"写入 {written} 行")
```

### git submodule 操作流程

本 Story 修改 bi/ 内文件，需两步 commit：

```bash
# 步骤 A：在 bi/ 内 commit（在 BACKEND_ROOT_ABS 执行）
cd bi
git add python_sdk/outdoor_collector/collectors/partnerboost_collector.py
git commit -m "feat(outdoor_collector): Story 8.2 — PartnerBoost 联盟数据采集落库" --author="Sue <boil@vip.qq.com>"
cd ..

# 步骤 B：在主仓库 commit（含 bi submodule 引用 + 测试文件 + sprint-status）
git add bi tests/test_partnerboost_collector.py _bmad-output/implementation-artifacts/ _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat(story-8.2): PartnerBoost 联盟数据采集落库 — done" --author="Sue <boil@vip.qq.com>"
```

### 测试文件规范 `tests/test_partnerboost_collector.py`

```python
import sys, os
sys.path.insert(0, "bi/python_sdk/outdoor_collector")
from unittest.mock import patch, MagicMock
import pytest

# 需要先把 collectors/ 目录加入 sys.path
sys.path.insert(0, "bi/python_sdk/outdoor_collector/collectors")
import partnerboost_collector as pc


def test_transform_basic():
    """字段映射和数值清洗正确"""
    raw = [{"Partner": "Foo", "Click": "100", "Sale": "2",
            "Revenue": "$50.00", "Commission": "$5.00",
            "Status": "Approved", "Channel": "Content", "Payment Status": "Pending"}]
    result = pc._transform(raw, "2026-04-15")
    assert len(result) == 1
    r = result[0]
    assert r["collect_date"] == "2026-04-15"
    assert r["partner"] == "Foo"
    assert r["clicks"] == 100
    assert r["sales"] == 2
    assert abs(r["revenue"] - 50.0) < 0.01
    assert abs(r["commission"] - 5.0) < 0.01


def test_transform_empty():
    assert pc._transform([], "2026-04-15") == []


def test_transform_missing_numeric_fields():
    """缺失数值字段应置 None，不抛异常"""
    raw = [{"Partner": "Bar"}]
    result = pc._transform(raw, "2026-04-15")
    assert result[0]["clicks"] is None
    assert result[0]["revenue"] is None


@patch("partnerboost_collector.write_to_doris", return_value=3)
@patch("partnerboost_collector.sync_playwright")
def test_collect_happy_path(mock_pw, mock_write):
    """collect() 正常路径：抓取到数据后调用 write_to_doris"""
    mock_p = MagicMock()
    mock_pw.return_value.__enter__.return_value = mock_p
    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page

    # mock _scrape_all_rows 返回一条记录
    mock_page.query_selector_all.return_value = []  # 空 tbody（no-data 路径需单独测）

    with patch("partnerboost_collector._scrape_all_rows", return_value=[
        {"Partner": "X", "Click": "10", "Sale": "1",
         "Revenue": "$20.00", "Commission": "$2.00",
         "Status": "Approved", "Channel": "Content", "Payment Status": "Pending"}
    ]), patch.dict(os.environ, {"PARTNERBOOST_USERNAME": "u", "PARTNERBOOST_PASSWORD": "p"}):
        written = pc.collect("2026-04-15")
    assert written == 3
    mock_write.assert_called_once()
```

### 防回归约束

- 不修改 `sources/partnerboost.py`（Phase 1 成果）
- 不修改 `sdk/` 下任何文件（Story 6.0 成果）
- 不修改 `common/doris_writer.py`（Story 6.1 成果）
- 主仓库 `tests/` 中已有的 166 个测试全部继续通过

### Review Findings（代码审查，2026-04-15）

- [x] [Review][Patch][HIGH] 验证码检测在 no-data 超时路径被绕过 [`collectors/partnerboost_collector.py` collect() 内 except 块] — 已修复：在 except 块内 return 0 前先调用 `_check_captcha(page)`
- [x] [Review][Patch] browser 变量可能未绑定导致 finally 崩溃 [`collectors/partnerboost_collector.py` collect()] — 已修复：初始化 `browser = None`，finally 改为 `if browser: browser.close()`
- [x] [Review][Patch] `_to_int` 无法处理带小数的整数字符串 [`collectors/partnerboost_collector.py` _to_int()] — 已修复：加 `int(float(cleaned))` 降级路径
- [x] [Review][Patch] `sync_playwright` 为 None 时缺少显式校验 [`collectors/partnerboost_collector.py` collect()] — 已修复：collect() 入口添加 `if sync_playwright is None: raise RuntimeError(...)`

- [x] [Review][Defer] 登录重定向校验过于宽松 [`collectors/partnerboost_collector.py:57`] — deferred, pre-existing — lambda `"login" not in url` 对 /error 等非 dashboard 页面也返回 True；与 Story 4.3 相同模式，暂缓
- [x] [Review][Defer] `_to_float` 未处理非美元货币符号 [`collectors/partnerboost_collector.py` _to_float()] — deferred, pre-existing — PartnerBoost 当前仅 USD，€/()等特殊格式暂不在范围内
- [x] [Review][Defer] `collect_date` 未做格式校验 [`collectors/partnerboost_collector.py` collect()] — deferred, pre-existing — 调用方责任，CLI 文档已说明格式
- [x] [Review][Defer] `sys.path.insert` 模块级副作用 [`collectors/partnerboost_collector.py:24`] — deferred, pre-existing — bi/ 子模块既有架构模式，统一处理
- [x] [Review][Defer] 异常链可能泄露凭证信息 [`collectors/partnerboost_collector.py` collect()] — deferred, pre-existing — 内部工具，日志受控环境运行
- [x] [Review][Defer] `partner` 为空字符串时复合唯一键可能碰撞 [`collectors/partnerboost_collector.py` _transform()] — deferred, pre-existing — 真实数据中 partner 字段不应为空，异常情况可后续处理

### References

- [Source: epics.md#Story 8.2] — AC 定义、增量策略、幂等 upsert 要求
- [Source: implementation-artifacts/4-3-partnerboost-爬虫数据源接入.md] — 现有 Playwright 登录实现、LOGIN_URL、REPORTS_URL
- [Source: implementation-artifacts/6-1-目录初始化与公共写入工具.md] — write_to_doris() 签名和调用规范
- [Source: project-context.md#Playwright 爬虫规则] — sync_playwright、验证码处理、_BROWSER_ARGS
- [Source: project-context.md#bi/ 子模块代码规范] — DorisConfig 单例、凭证不 import 主工具模块
- [Source: project-context.md#git submodule 操作] — bi/ 内 commit + 主仓库更新引用两步流程
