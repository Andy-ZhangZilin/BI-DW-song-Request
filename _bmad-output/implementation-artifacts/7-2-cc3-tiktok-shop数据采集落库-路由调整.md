# Story 7.2-CC3：TikTok Shop 数据采集落库 - 路由调整

Status: ready-for-dev

## Story

作为数据工程师，
我希望根据 CC#3 验证结果调整 TikTok Shop 采集路由，
以便采集实际有数据的接口，移除无效接口。

## Background

**CC#3 发现（2026-04-16）：**
- Story 7-2 实现了 6 个路由，但验证报告显示只有 4 个接口返回有效数据
- 缺失接口：`shop_video_performance_detail`（28 条数据）
- 无效接口：`affiliate_campaign_performance`、`affiliate_sample_status`（0 条数据）
- 未验证接口：`affiliate_creator_orders`（从未出现在验证报告中）

## Acceptance Criteria

1. **Given** 当前 ROUTES 配置有 6 个路由；**When** 更新为 CC#3 提案；**Then** 保留 4 个有效路由：`return_refund`、`video_performances`、`shop_product_performance`、`shop_video_performance_detail`

2. **Given** 新增 `shop_video_performance_detail` 路由；**When** 采集时；**Then** 调用 `/analytics/202509/shop_videos/{video_id}/performance/detail` 接口，返回 28 条数据

3. **Given** 移除 3 个无效路由；**When** 代码中；**Then** 删除 `_collect_affiliate_creator_orders()`、`_collect_affiliate_campaign_performance()`、`_collect_affiliate_sample_status()` 函数

4. **Given** Doris 表结构；**When** 创建新表；**Then** 创建 `hqware_test.ods_tiktok_shop_video_performance_detail` 表

5. **Given** 所有测试；**When** 运行；**Then** 所有单元测试通过

## Tasks / Subtasks

- [ ] Task 1: 更新 tiktok_collector.py
  - [ ] 1.1 更新 ROUTES 配置：移除 3 个路由，新增 `shop_video_performance_detail`
  - [ ] 1.2 新增 `_collect_shop_video_performance_detail(client, start_date, end_date)` 函数
  - [ ] 1.3 新增 `_fetch_video_ids(client, start_date, end_date)` 辅助函数
  - [ ] 1.4 删除 `_collect_affiliate_creator_orders()` 函数
  - [ ] 1.5 删除 `_collect_affiliate_campaign_performance()` 函数
  - [ ] 1.6 删除 `_collect_affiliate_sample_status()` 函数
  - [ ] 1.7 删除 `_fetch_campaigns()` 函数
  - [ ] 1.8 删除 `_fetch_category_asset_cipher()` 函数
  - [ ] 1.9 删除 `_fetch_campaign_products()` 函数
  - [ ] 1.10 删除 `_fetch_creator_temp_id()` 函数
  - [ ] 1.11 更新 `collect()` 函数中的路由分支逻辑

- [ ] Task 2: 创建 Doris 表
  - [ ] 2.1 在 `init_doris_tables.py` 中新增 `ods_tiktok_shop_video_performance_detail` 表定义

- [ ] Task 3: 更新测试
  - [ ] 3.1 更新 `tests/test_tiktok_collector.py`：移除 3 个无效路由的测试
  - [ ] 3.2 新增 `_collect_shop_video_performance_detail()` 的测试用例

- [ ] Task 4: 更新文档
  - [ ] 4.1 更新 Story 7-2 的 AC（从 6 个路由改为 4 个）
  - [ ] 4.2 更新 sprint-status.yaml（7-2 标记为 in-progress）

## Dev Notes

### 新增函数实现

```python
def _collect_shop_video_performance_detail(
    client: TikTokClient, start_date: str, end_date: str
) -> list[dict]:
    """GET /analytics/202509/shop_videos/{video_id}/performance/detail — 视频详细表现。

    先获取视频 ID 列表，再逐一查询详细数据。
    """
    # 先获取视频 ID 列表
    video_ids = _fetch_video_ids(client, start_date, end_date)
    if not video_ids:
        logger.warning(f"[{SOURCE}][shop_video_performance_detail] 无视频 ID，跳过")
        return []

    data_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    all_records: list[dict] = []
    for video_id in video_ids:
        path = f"/analytics/202509/shop_videos/{video_id}/performance/detail"
        extra_params: dict = {
            "start_date_ge": start_date,
            "end_date_lt":   end_date,
        }
        try:
            resp = client.get(path, params=extra_params)
            _check_code(resp, path)
            data = resp.get("data") or {}
            record = {"video_id": video_id, "collect_date": data_date}
            record.update(data)
            all_records.append(record)
        except RuntimeError as e:
            logger.warning(f"[{SOURCE}][shop_video_performance_detail] video_id={video_id} 查询失败：{e}")
            continue

    logger.info(f"[{SOURCE}][shop_video_performance_detail] 获取 {len(all_records)} 条视频详细表现")
    return all_records


def _fetch_video_ids(client: TikTokClient, start_date: str, end_date: str) -> list[str]:
    """从 video_performances 接口获取视频 ID 列表。"""
    path = "/analytics/202509/shop_videos/performance"
    extra_params: dict = {
        "start_date_ge": start_date,
        "end_date_lt":   end_date,
        "page_size":     "100",
    }
    try:
        resp = client.get(path, params=extra_params)
        _check_code(resp, path)
        videos = (resp.get("data") or {}).get("videos") or []
        return [v["video_id"] for v in videos if v.get("video_id")]
    except RuntimeError as e:
        logger.warning(f"[{SOURCE}] 获取视频 ID 列表失败：{e}")
        return []
```

### 新增 Doris 表 DDL

```sql
CREATE TABLE IF NOT EXISTS hqware_test.ods_tiktok_shop_video_performance_detail (
    video_id        VARCHAR(64),
    collect_date    DATE,
    latest_available_date VARCHAR(50),
    likes           BIGINT,
    comments        BIGINT,
    shares          BIGINT,
    views           BIGINT,
    customers       BIGINT,
    gmv_amount      DECIMAL(18,4),
    gmv_currency    VARCHAR(10),
    raw_json        TEXT,
    collected_at    DATETIME DEFAULT NOW()
) ENGINE=OLAP UNIQUE KEY(video_id, collect_date) DISTRIBUTED BY HASH(video_id) BUCKETS 10
```

## Success Criteria

- ✅ ROUTES 配置已更新为 4 个路由
- ✅ 新增 `_collect_shop_video_performance_detail()` 函数
- ✅ 3 个无效函数已删除
- ✅ 所有相关辅助函数已删除
- ✅ Doris 表已创建
- ✅ 所有测试通过
- ✅ Story 7-2 文档已更新
- ✅ sprint-status.yaml 已更新

## Related Documents

- CC#3 提案：`_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-16-cc3.md`
- Story 7-2 原始文档：`_bmad-output/implementation-artifacts/7-2-tiktok-shop数据采集落库.md`
