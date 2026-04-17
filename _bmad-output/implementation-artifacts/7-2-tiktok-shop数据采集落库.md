# Story 7.2：TikTok Shop 数据采集落库

Status: review

## Story

作为数据工程师，
我希望能将 TikTok Shop 的订单、商品、视频及联盟数据采集并写入 Doris，
以便后续构建 TikTok 销售表和联盟营销报表。

## Acceptance Criteria

1. **Given** TikTok 凭证有效（DTC 中间层可访问）；**When** 运行 `tiktok_collector.py`；**Then** 调用 `sdk/tiktok/TikTokClient` 完成 DTC 两步认证，不重复实现 HmacSHA256 签名和 token 换取逻辑
2. **Given** 认证成功；**When** 采集 6 个路由；**Then** 分别采集：`return_refund`、`affiliate_creator_orders`、`video_performances`、`shop_product_performance`、`affiliate_campaign_performance`、`affiliate_sample_status`
3. **Given** 订单类路由（return_refund、affiliate_creator_orders）；**When** 增量模式运行；**Then** 使用归因窗口：`start_time = 水位线时间 - 3天`，补充晚到订单
4. **Given** 各路由写入成功；**When** 查看 Doris；**Then** 每个路由写入独立 Doris 表（`hqware.ods_tiktok_{route}`），upsert 幂等写入
5. **Given** 首次运行（无水位线）；**When** 执行全量拉取；**Then** 拉取默认起始时间（或 `--start-date` 参数）到今天的数据
6. **Given** `--mode full` 参数；**When** 运行；**Then** 先调用 `reset_watermark`，再全量重拉所有数据
7. **Given** 单个路由采集失败；**When** 其他路由正常；**Then** 失败不传染（try/except 隔离），仍继续采集其余路由并输出 warning
8. **Given** 无数据（API 返回空列表）；**When** 该路由运行；**Then** 跳过写入，记录 info 日志，不抛异常
9. **Given** 单元测试环境；**When** 运行 `tests/test_tiktok_collector.py`；**Then** 所有单元测试通过（mock TikTokClient + mock write_to_doris）

## Tasks / Subtasks

- [ ] Task 1: 实现 `bi/python_sdk/outdoor_collector/collectors/tiktok_collector.py` (AC: 1-8)
  - [ ] 1.1 定义常量：SOURCE、ROUTES 配置表（6 路由 → 表名 + unique_keys + 时间字段）、ATTRIBUTION_WINDOW_DAYS = 3
  - [ ] 1.2 实现 `_get_client()` — 加载 .env 凭证，初始化 TikTokClient 并调用 authenticate()
  - [ ] 1.3 实现 `_collect_return_refund(client, start_ts, end_ts)` — 翻页拉取退款记录
  - [ ] 1.4 实现 `_collect_affiliate_creator_orders(client, start_ts, end_ts)` — 翻页拉取达人订单
  - [ ] 1.5 实现 `_collect_video_performances(client, start_date, end_date)` — 拉取视频表现（日期范围）
  - [ ] 1.6 实现 `_collect_shop_product_performance(client, start_date, end_date)` — 翻页拉取商品表现
  - [ ] 1.7 实现 `_collect_affiliate_campaign_performance(client, start_date, end_date)` — 拉取联盟活动表现
  - [ ] 1.8 实现 `_collect_affiliate_sample_status(client, start_date, end_date)` — 拉取联盟样品状态
  - [ ] 1.9 实现 `collect(mode, route, start_date)` — 主入口：初始化 client → 遍历 6 路由 → 水位线判断 → 调用采集函数 → 写入 Doris → 更新水位线
  - [ ] 1.10 实现 `if __name__ == "__main__"` — 解析 `--mode`、`--route`、`--start-date`、`--dry-run` 参数

- [ ] Task 2: 编写单元测试 `tests/test_tiktok_collector.py` (AC: 9)
  - [ ] 2.1 测试 `collect()` 正常路径（mock TikTokClient.authenticate + 各路由 client.post/get + mock write_to_doris）
  - [ ] 2.2 测试单路由失败不影响其他路由（模拟 _collect_return_refund 抛出 RuntimeError）
  - [ ] 2.3 测试空数据路由跳过写入（mock 返回空列表）
  - [ ] 2.4 测试 `--mode full` 触发 reset_watermark + 全量拉取

- [ ] Task 3: 更新 sprint-status.yaml
  - [ ] 3.1 `epic-7` → `in-progress`，`7-2-tiktok-shop数据采集落库` → `done`

## Dev Notes

### 文件结构

```
bi/python_sdk/outdoor_collector/
└── collectors/
    └── tiktok_collector.py        ← 本 Story 核心新建文件

outdoor-data-validator/            ← 主仓库
└── tests/
    └── test_tiktok_collector.py   ← 单元测试
```

> **禁止修改：**
> - `sources/tiktok.py`（Phase 1 成果，三函数契约）
> - `sdk/tiktok/auth.py`、`sdk/tiktok/client.py`（Story 6.0 成果）
> - `common/doris_writer.py`、`common/watermark.py`（Story 6.1/6.2 成果）

---

### 关键依赖与导入规范

```python
# tiktok_collector.py 文件头部标准写法
import sys
import os
import logging
import argparse
from datetime import datetime, timedelta, date as _date
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent   # outdoor_collector/
sys.path.insert(0, str(_ROOT))

from sdk.tiktok import TikTokClient              # Story 6.0
from common.doris_writer import write_to_doris   # Story 6.1
from common.watermark import get_watermark, update_watermark, reset_watermark  # Story 6.2

load_dotenv()                                    # 加载 .env（含 TIKTOK_APP_KEY 等）

logger = logging.getLogger(__name__)
```

> **关键**：凭证通过 `python-dotenv` 加载，不使用主工具的 `config.credentials`（两个独立模块）。

---

### 凭证加载

```python
def _get_client() -> TikTokClient:
    """加载凭证并初始化已认证的 TikTokClient。"""
    app_key    = os.environ.get("TIKTOK_APP_KEY", "")
    app_secret = os.environ.get("TIKTOK_APP_SECRET", "")
    if not app_key or not app_secret:
        raise RuntimeError("[tiktok_collector] 未配置 TIKTOK_APP_KEY / TIKTOK_APP_SECRET")
    client = TikTokClient(app_key=app_key, app_secret=app_secret)
    client.authenticate()   # DTC 两步换取 access_token + shop_cipher，失败抛 RuntimeError
    return client
```

> TikTokClient.authenticate() 通过 DTC 中间层认证（见 `sdk/tiktok/auth.py`），每次调用重新获取，无需手动管理 token。

---

### 6 路由配置表

```python
SOURCE = "tiktok_collector"

# 全局日期范围（当无水位线时的默认起始）
EARLIEST_DATE = "2024-01-01"
# 订单归因窗口（晚到订单补偿）
ATTRIBUTION_WINDOW_DAYS = 3

ROUTES: dict = {
    # --- 订单类（时间戳过滤，归因窗口 3 天） ---
    "return_refund": {
        "table":       "hqware.ods_tiktok_return_refund",
        "unique_keys": ["return_id"],
        "type":        "order",   # 使用 unix 时间戳过滤
    },
    "affiliate_creator_orders": {
        "table":       "hqware.ods_tiktok_affiliate_creator_orders",
        "unique_keys": ["order_id"],
        "type":        "order",
    },
    # --- 分析类（日期过滤，无归因窗口） ---
    "video_performances": {
        "table":       "hqware.ods_tiktok_video_performances",
        "unique_keys": ["video_id", "collect_date"],
        "type":        "analytics",
    },
    "shop_product_performance": {
        "table":       "hqware.ods_tiktok_shop_product_performance",
        "unique_keys": ["product_id", "collect_date"],
        "type":        "analytics",
    },
    "affiliate_campaign_performance": {
        "table":       "hqware.ods_tiktok_affiliate_campaign_performance",
        "unique_keys": ["campaign_id", "product_id", "collect_date"],
        "type":        "analytics",
    },
    "affiliate_sample_status": {
        "table":       "hqware.ods_tiktok_affiliate_sample_status",
        "unique_keys": ["campaign_id", "product_id", "creator_temp_id", "collect_date"],
        "type":        "analytics",
    },
}
```

---

### 增量水位线逻辑

```python
def _get_time_range(route_key: str, cfg: dict, mode: str, start_date_arg: str | None):
    """根据水位线计算本次拉取的时间范围。

    Returns:
        (start_ts, end_ts) — 订单类（unix 时间戳，int）
        (start_date, end_date) — 分析类（YYYY-MM-DD str）
    """
    table = cfg["table"]
    wm = get_watermark(SOURCE, table)

    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    if mode == "full" or wm is None:
        # 全量：从 EARLIEST_DATE 或用户指定日期开始
        start = start_date_arg or EARLIEST_DATE
    else:
        last_ok = wm["last_success_time"]  # datetime 对象
        if cfg["type"] == "order":
            # 订单类：回溯 3 天归因窗口
            start_dt = last_ok - timedelta(days=ATTRIBUTION_WINDOW_DAYS)
            start = start_dt.strftime("%Y-%m-%d")
        else:
            start = last_ok.strftime("%Y-%m-%d")

    if cfg["type"] == "order":
        # 订单类：转 unix 时间戳
        start_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        end_ts   = int(now.timestamp())
        return start_ts, end_ts
    else:
        # 分析类：日期字符串
        return start, today_str
```

---

### TikTokClient API 调用规范

TikTokClient 已封装签名逻辑，直接调用 `client.get()` / `client.post()`：

```python
# 订单类示例（return_refund，需翻页）
def _collect_return_refund(client: TikTokClient, start_ts: int, end_ts: int) -> list[dict]:
    path = "/return_refund/202602/returns/search"
    all_records: list[dict] = []
    page_token = None
    while True:
        body: dict = {
            "page_size": 100,
            "create_time_ge": start_ts,
            "create_time_lt": end_ts,
        }
        if page_token:
            body["page_token"] = page_token
        resp = client.post(path, body=body)
        _check_code(resp, path)
        data = resp.get("data") or {}
        # API 返回字段名：return_orders 或 returns 或 return_list（兼容多版本）
        for key in ("return_orders", "returns", "return_list"):
            records = data.get(key)
            if records:
                break
        records = records or []
        all_records.extend(records)
        page_token = data.get("next_page_token")
        if not page_token:
            break
    return all_records


# 分析类示例（video_performances，日期过滤，单页）
def _collect_video_performances(client: TikTokClient, start_date: str, end_date: str) -> list[dict]:
    path = "/analytics/202509/shop_videos/performance"
    all_records: list[dict] = []
    page_token = None
    while True:
        extra_params: dict = {
            "start_date_ge": start_date,
            "end_date_lt": end_date,
            "page_size": "100",
        }
        if page_token:
            extra_params["page_token"] = page_token
        resp = client.get(path, params=extra_params)
        _check_code(resp, path)
        data = resp.get("data") or {}
        videos = data.get("videos") or []
        # 展平：每条视频 + collect_date
        for v in videos:
            v["collect_date"] = end_date
        all_records.extend(videos)
        page_token = data.get("next_page_token")
        if not page_token:
            break
    return all_records
```

**helper:**

```python
def _check_code(resp: dict, path: str) -> None:
    """检查 API 响应 code，非 0 抛 RuntimeError。"""
    code = resp.get("code")
    if code != 0:
        raise RuntimeError(
            f"[tiktok_collector] {path} 返回错误 code={code}，message={resp.get('message')}"
        )
```

---

### 主入口 collect() 结构

```python
def collect(
    mode: str = "incremental",     # "incremental" | "full"
    route: str | None = None,      # None = 全部 6 个路由
    start_date: str | None = None, # 全量时起始日期，默认 EARLIEST_DATE
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Returns:
        {route_key: written_rows} — 各路由写入行数（0=无数据 or dry_run）
    """
    results: dict[str, int] = {}
    client = _get_client()

    target_routes = {route: ROUTES[route]} if route else ROUTES

    if mode == "full":
        for key, cfg in target_routes.items():
            reset_watermark(SOURCE, cfg["table"])

    for route_key, cfg in target_routes.items():
        table = cfg["table"]
        try:
            # 计算时间范围
            time_range = _get_time_range(route_key, cfg, mode, start_date)

            # 按路由分发采集函数
            if route_key == "return_refund":
                records = _collect_return_refund(client, *time_range)
            elif route_key == "affiliate_creator_orders":
                records = _collect_affiliate_creator_orders(client, *time_range)
            elif route_key == "video_performances":
                records = _collect_video_performances(client, *time_range)
            elif route_key == "shop_product_performance":
                records = _collect_shop_product_performance(client, *time_range)
            elif route_key == "affiliate_campaign_performance":
                records = _collect_affiliate_campaign_performance(client, *time_range)
            elif route_key == "affiliate_sample_status":
                records = _collect_affiliate_sample_status(client, *time_range)
            else:
                logger.warning(f"[tiktok_collector] 未知路由 {route_key}，跳过")
                continue

            if not records:
                logger.info(f"[tiktok_collector][{table}] 无数据，跳过写入")
                results[route_key] = 0
                continue

            if dry_run:
                logger.info(f"[tiktok_collector][{table}] dry_run，共 {len(records)} 条，不写入")
                results[route_key] = 0
                continue

            written = write_to_doris(table, records, cfg["unique_keys"], source=SOURCE)
            update_watermark(SOURCE, table, datetime.utcnow())
            results[route_key] = written

        except Exception as e:
            # 单路由失败不传染
            logger.warning(f"[tiktok_collector][{table}] 采集失败（已跳过）：{e}")
            results[route_key] = 0

    return results
```

---

### Doris 表 DDL 参考（由 DBA 建表，collector 不负责 DDL）

**表 1：退款记录**
```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tiktok_return_refund (
    return_id       VARCHAR(64)   NOT NULL COMMENT '退款 ID',
    order_id        VARCHAR(64)   COMMENT '订单 ID',
    status          VARCHAR(32)   COMMENT '退款状态',
    reason          VARCHAR(256)  COMMENT '退款原因',
    create_time     BIGINT        COMMENT 'Unix 时间戳',
    update_time     BIGINT        COMMENT '更新时间戳',
    shop_id         VARCHAR(64)   COMMENT '店铺 ID',
    shop_name       VARCHAR(256)  COMMENT '店铺名称',
    raw_json        TEXT          COMMENT '原始响应（保留冗余字段）',
    collected_at    DATETIME DEFAULT NOW()
) UNIQUE KEY(return_id)
DISTRIBUTED BY HASH(return_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

**表 2：达人订单**
```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tiktok_affiliate_creator_orders (
    order_id        VARCHAR(64)   NOT NULL COMMENT '订单 ID',
    creator_id      VARCHAR(64)   COMMENT '达人 ID',
    status          VARCHAR(32)   COMMENT '订单状态',
    sale_amount     DECIMAL(18,4) COMMENT '销售金额',
    commission      DECIMAL(18,4) COMMENT '佣金',
    create_time     BIGINT        COMMENT 'Unix 时间戳',
    raw_json        TEXT          COMMENT '原始响应',
    collected_at    DATETIME DEFAULT NOW()
) UNIQUE KEY(order_id)
DISTRIBUTED BY HASH(order_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

**表 3-6：analytics 类（示例 video_performances，其余类似）**
```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tiktok_video_performances (
    video_id        VARCHAR(64)   NOT NULL COMMENT '视频 ID',
    collect_date    DATE          NOT NULL COMMENT '采集日期',
    title           VARCHAR(512)  COMMENT '视频标题',
    views           BIGINT        COMMENT '播放数',
    likes           BIGINT        COMMENT '点赞数',
    shares          BIGINT        COMMENT '分享数',
    comments        BIGINT        COMMENT '评论数',
    raw_json        TEXT          COMMENT '原始响应',
    collected_at    DATETIME DEFAULT NOW()
) UNIQUE KEY(video_id, collect_date)
DISTRIBUTED BY HASH(video_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

> **注意**：analytics 类表字段以实际 API 响应为准，DDL 定义后请 DBA 在 hqware 库建表。

---

### `_collect_affiliate_creator_orders` 特殊规范

来自 `sources/tiktok.py` 验证结论：
- `page_size` 必须在 **query params**（参与签名），**不能放 body**，否则报错 `36009004`
- `client.post()` 的 `params` 参数对应额外 query params，`body` 对应 POST body

```python
def _collect_affiliate_creator_orders(client: TikTokClient, start_ts: int, end_ts: int) -> list[dict]:
    path = "/affiliate_creator/202410/orders/search"
    all_records: list[dict] = []
    page_token = None
    while True:
        # page_size 必须在 params（query string），不在 body
        extra_params: dict = {"page_size": "100"}
        if page_token:
            extra_params["page_token"] = page_token
        body: dict = {"create_time_ge": start_ts, "create_time_lt": end_ts}
        resp = client.post(path, params=extra_params, body=body)
        _check_code(resp, path)
        data = resp.get("data") or {}
        orders = data.get("orders") or []
        all_records.extend(orders)
        page_token = data.get("next_page_token")
        if not page_token:
            break
    return all_records
```

---

### `_collect_shop_product_performance` 特殊规范

来自 `sources/tiktok.py` 验证结论：
- 路径含动态 `product_id`：`/analytics/202509/shop_products/{product_id}/performance`
- 需先通过 `/product/202309/products/search` 获取 product_id 列表
- 每个 product_id 独立请求，合并结果
- **不要重复实现 product_id 获取逻辑**：可以直接调用 `client.post("/product/202309/products/search", body={"page_size": 50})` 获取
- 响应结构：`data.performance.intervals[{start_date, end_date, sales, traffic, ...}]`

---

### 日志格式规范

```python
# 标准格式（与 partnerboost_collector.py 保持一致）
logger.info(f"[{SOURCE}][{table}] 写入 {written} 行 ... 成功")        # write_to_doris 内部已输出
logger.info(f"[{SOURCE}][{table}] 无数据，跳过写入")
logger.warning(f"[{SOURCE}][{table}] 采集失败（已跳过）：{e}")
```

---

### 测试文件规范

```python
# tests/test_tiktok_collector.py
import sys
import os
from unittest.mock import patch, MagicMock
import pytest

# 将 outdoor_collector 根目录加入路径（与 test_partnerboost_collector.py 相同约定）
sys.path.insert(0, "bi/python_sdk/outdoor_collector")
sys.path.insert(0, "bi/python_sdk/outdoor_collector/collectors")

import tiktok_collector as tc


@patch("tiktok_collector.write_to_doris", return_value=10)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.TikTokClient")
@patch.dict(os.environ, {"TIKTOK_APP_KEY": "test_key", "TIKTOK_APP_SECRET": "test_secret"})
def test_collect_all_routes_happy_path(mock_client_cls, mock_get_wm, mock_upd_wm, mock_write):
    """collect() 正常路径：6 个路由均写入成功"""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    # 各路由 post/get 返回带一条记录的响应
    mock_client.post.return_value = {"code": 0, "data": {"return_orders": [{"return_id": "r1"}]}}
    mock_client.get.return_value  = {"code": 0, "data": {"videos": [{"id": "v1", "views": 100}]}}

    with patch.object(tc, "_collect_return_refund", return_value=[{"return_id": "r1"}]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[{"order_id": "o1"}]), \
         patch.object(tc, "_collect_video_performances", return_value=[{"video_id": "v1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[{"product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[{"campaign_id": "c1", "product_id": "p1", "collect_date": "2026-01-01"}]), \
         patch.object(tc, "_collect_affiliate_sample_status", return_value=[{"campaign_id": "c1", "product_id": "p1", "creator_temp_id": "t1", "collect_date": "2026-01-01"}]):
        results = tc.collect(mode="incremental")

    assert len(results) == 6
    assert all(v == 10 for v in results.values())


@patch("tiktok_collector.write_to_doris", return_value=5)
@patch("tiktok_collector.update_watermark")
@patch("tiktok_collector.get_watermark", return_value=None)
@patch("tiktok_collector.TikTokClient")
@patch.dict(os.environ, {"TIKTOK_APP_KEY": "k", "TIKTOK_APP_SECRET": "s"})
def test_single_route_failure_does_not_propagate(mock_client_cls, mock_get_wm, mock_upd_wm, mock_write):
    """单路由失败不影响其他路由（AC7）"""
    mock_client_cls.return_value = MagicMock()

    def _raise(*a, **kw):
        raise RuntimeError("API error")

    with patch.object(tc, "_collect_return_refund", side_effect=_raise), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[{"order_id": "o1"}]), \
         patch.object(tc, "_collect_video_performances", return_value=[]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_sample_status", return_value=[]):
        results = tc.collect(mode="incremental")

    assert results["return_refund"] == 0         # 失败路由 = 0
    assert results["affiliate_creator_orders"] == 5  # 其他路由正常


def test_collect_empty_data_skips_write():
    """空数据路由跳过写入，结果 = 0（AC8）"""
    with patch("tiktok_collector.TikTokClient") as mock_cls, \
         patch("tiktok_collector.write_to_doris") as mock_write, \
         patch("tiktok_collector.get_watermark", return_value=None), \
         patch("tiktok_collector.update_watermark"), \
         patch.dict(os.environ, {"TIKTOK_APP_KEY": "k", "TIKTOK_APP_SECRET": "s"}), \
         patch.object(tc, "_collect_return_refund", return_value=[]), \
         patch.object(tc, "_collect_affiliate_creator_orders", return_value=[]), \
         patch.object(tc, "_collect_video_performances", return_value=[]), \
         patch.object(tc, "_collect_shop_product_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_campaign_performance", return_value=[]), \
         patch.object(tc, "_collect_affiliate_sample_status", return_value=[]):
        mock_cls.return_value = MagicMock()
        results = tc.collect(mode="incremental")

    mock_write.assert_not_called()               # 无写入
    assert all(v == 0 for v in results.values())
```

---

### git submodule 操作流程

本 Story 修改 `bi/` 内文件，需两步 commit：

```bash
# 步骤 A：在 bi/ 内 commit（cd BACKEND_ROOT_ABS 后执行）
cd bi
git add python_sdk/outdoor_collector/collectors/tiktok_collector.py
git commit -m "feat(outdoor_collector): Story 7.2 — TikTok Shop 数据采集落库" \
    --author="jiuyueshang <845126847@qq.com>"
cd ..

# 步骤 B：在主仓库 commit（含 bi 引用 + 测试文件 + sprint-status）
git add bi tests/test_tiktok_collector.py \
    _bmad-output/implementation-artifacts/7-2-tiktok-shop数据采集落库.md \
    _bmad-output/implementation-artifacts/sprint-status.yaml
git commit -m "feat(story-7.2): TikTok Shop 数据采集落库 — done" \
    --author="jiuyueshang <845126847@qq.com>"
```

---

### 防回归约束

- 不修改 `sources/tiktok.py`（Phase 1 成果）
- 不修改 `sdk/` 下任何文件（Story 6.0 成果）
- 不修改 `common/doris_writer.py`、`common/watermark.py`（Story 6.1/6.2 成果）
- 主仓库 `tests/` 中**已有所有测试继续通过**（运行 `pytest tests/ -m "not integration"` 验证）

---

### References

- [Source: epics.md#Story 7.2] — AC 定义、归因窗口 3 天、6 接口路由
- [Source: architecture.md#Phase 2 Architecture] — 目录结构、TikTokClient 设计、水位线机制、write_to_doris 签名
- [Source: implementation-artifacts/6-0-api客户端sdk层建立.md] — TikTokClient 接口规范、DTC 认证流程
- [Source: implementation-artifacts/6-1-目录初始化与公共写入工具.md] — write_to_doris() 调用规范
- [Source: implementation-artifacts/6-2-水位线管理器.md] — get/update/reset_watermark 接口
- [Source: implementation-artifacts/2-2-tiktok-shop-数据源接入.md] — `affiliate_creator_orders page_size 必须在 query params`、DTC 认证流程细节、签名算法
- [Source: sources/tiktok.py TABLES] — 6 个已验证路由名称和 API 路径
- [Source: collectors/partnerboost_collector.py] — bi/ collector 代码风格参考（load_dotenv、sys.path、write_to_doris 调用）

---

### Review Findings

> 代码审查于 2026-04-16 完成（3 层并行：Blind Hunter + Edge Case Hunter + Acceptance Auditor）

#### Decision Needed（需人工决策）

- [ ] [Review][Decision] D1: `_fetch_creator_temp_id` 未将 campaign_id/product_id 传入请求 body — 函数签名接收两个参数但 `body={}` 为空，返回任意订单的 creator_temp_id，导致 `affiliate_sample_status` 数据语义错误；正确修复方式取决于 TikTok API 是否支持按 campaign/product 过滤该接口
- [ ] [Review][Decision] D2: `collect_date = end_date` 语义疑问 — 6 个分析类路由均以 `end_date_lt`（排除上界）的值作为 `collect_date` 注入；若 `end_date` 是今天，实际数据对应的是昨天，请确认 `collect_date` 应存今天还是昨天

#### Patch（可直接修复）

- [ ] [Review][Patch] P1: `_fetch_category_asset_cipher` 冗余首次 `client.get()` 调用 — 函数先调用 `client.get()` 发起真实 HTTP 请求但不使用其结果，随即重新 `import requests` 直接发起裸请求，浪费 rate-limit 配额且绕过 client 抽象；应移除第一行 `client.get` 调用 [tiktok_collector.py:365]
- [ ] [Review][Patch] P2: `update_watermark` 缺少 `written > 0` 守护 — 写入 0 行时也会推进水位线，导致下次增量漏拉该窗口数据 [tiktok_collector.py:544]
- [ ] [Review][Patch] P3: `record.update(interval/perf/data)` 可覆盖注入 key — `product_id`、`campaign_id`、`collect_date` 先注入再 update，若 API 响应包含同名字段会被静默覆盖；应先 update 再注入 metadata [tiktok_collector.py:280,333,436]
- [ ] [Review][Patch] P4: `_check_code` 未处理 `code=None` — `resp.get("code")` 返回 None 时 `None != 0` 为 True，误判为业务错误；应先判断 `if code is None: return`（或 `raise`，按业务需求定）[tiktok_collector.py:121]
- [ ] [Review][Patch] P5: `_collect_affiliate_campaign_performance` fallback `perf_list = [data]` — 当 `perf_list` 为空时将整个 `data` 对象（含元数据字段）当作记录写入，会污染下游表；应移除此 fallback 并记录 warning [tiktok_collector.py:330]

#### Deferred（预存在问题，暂不处理）

- [x] [Review][Defer] W1: `last_ok` 类型假设（datetime）— 若水位线持久化为字符串则会在减法运算时崩溃；依赖 Story 6.2 实现保证，暂 defer [tiktok_collector.py:142]
- [x] [Review][Defer] W2: 翻页循环缺少最大页数保护 — 无限循环风险，建议生产环境加 max_pages 计数器；非关键 bug，defer [tiktok_collector.py:168,203,232]
- [x] [Review][Defer] W3: `datetime.utcnow()` vs timezone-aware datetime — 全 codebase 一致模式，需统一升级，defer [tiktok_collector.py:136]
- [x] [Review][Defer] W4: `_fetch_product_ids` / `_fetch_campaigns` 无翻页（硬限 50 条）— 已知限制，大规模店铺数据不完整，defer
- [x] [Review][Defer] W5: full mode `reset_watermark` 批量执行后进程中断无法恢复 — 架构设计问题，defer
- [x] [Review][Defer] W6: `sys.path.insert` 永久修改 — 全 codebase 一致模式，defer
