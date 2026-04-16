# Story 7.4：YouTube 视频统计数据采集落库（钉钉 URL 驱动）

Status: done

## Story

作为数据工程师，
我希望基于钉钉表中的视频 URL 字段，自动拉取对应 YouTube 视频的统计数据并写入 Doris，
以便 KOL 内容表可以关联真实播放数据。

## Acceptance Criteria

1. **Given** `YOUTUBE_API_KEY` 环境变量已配置；**When** 运行 `youtube_collector.py`；**Then** 从 Doris 表 `hqware.ods_dingtalk_kol_tidwe_content` 读取 `*内容发布链接` 字段，仅处理 YouTube 域名链接（`youtube.com/watch?v=`、`youtu.be/`、`youtube.com/shorts/`）

2. **Given** 读取到 YouTube URL；**When** 提取 video_id；**Then** 调用 YouTube Data API v3 `videos.list`（`part=snippet,statistics`）获取 viewCount、likeCount、commentCount、duration 等统计数据

3. **Given** 首次运行（YouTube 统计表中无该 video_id 记录）；**When** 采集完成；**Then** 写入 `hqware.ods_youtube_video_stats`，以 `video_id` 为唯一主键做 upsert

4. **Given** 非首次运行（video_id 已存在）；**When** 采集完成；**Then** 刷新统计数据（upsert 覆盖），更新 `collected_at` 字段

5. **Given** URL 无法解析 video_id（格式不支持）；**When** 处理该记录；**Then** 记录 warning 日志并跳过，不中断其他记录处理

6. **Given** YouTube API 返回空结果（视频已删除/私有）；**When** 处理该 video_id；**Then** 记录 warning 日志并跳过，不中断其他记录处理

7. **Given** YouTube API 配额超限（HTTP 403）；**When** 请求失败；**Then** 抛出 `RuntimeError`，中断采集，不静默失败

8. **Given** 单元测试环境；**When** 运行 `tests/test_youtube_collector.py`；**Then** 所有单元测试通过（mock pymysql + mock requests + mock write_to_doris）

## Tasks / Subtasks

- [x] Task 1：实现 `collectors/youtube_collector.py`（AC: 1–7）
  - [x] 1.1 定义常量和环境变量读取（`YOUTUBE_API_KEY`、`YOUTUBE_API_BASE`、`HTTP_TIMEOUT`、`BATCH_SIZE`）
  - [x] 1.2 实现 `_fetch_urls_from_doris() -> list[dict]`：从 `hqware.ods_dingtalk_kol_tidwe_content` 读取 `record_id` 和 `*内容发布链接` 字段，返回全部记录
  - [x] 1.3 实现 `_is_youtube_url(url: str) -> bool`：判断是否为 YouTube 域名链接
  - [x] 1.4 复用 `sources/youtube.py` 中的 `extract_video_id(url)` 逻辑（**直接复制函数，不 import 主工具模块**）
  - [x] 1.5 实现 `_fetch_video_stats(video_ids: list[str], api_key: str) -> list[dict]`：批量调用 YouTube API（每次最多 50 个 video_id），返回统计数据列表
  - [x] 1.6 实现 `_transform(raw_items: list[dict], record_id_map: dict) -> list[dict]`：将 API 响应映射为 Doris 格式
  - [x] 1.7 实现 `collect() -> int`：主入口（读 URL → 过滤 YouTube → 批量拉取统计 → upsert 写入 → 更新水位线）
  - [x] 1.8 实现 `if __name__ == "__main__"` 入口，支持 `--dry-run` 参数

- [x] Task 2：编写单元测试 `tests/test_youtube_collector.py`（AC: 8）
  - [x] 2.1 测试 `_is_youtube_url()`：YouTube 域名返回 True，其他域名返回 False
  - [x] 2.2 测试 `extract_video_id()`：watch?v=、youtu.be/、shorts/ 三种格式
  - [x] 2.3 测试 `_transform()`：字段映射、类型转换、commentCount 为 None 时写 NULL
  - [x] 2.4 测试 `collect()` 正常路径（mock Doris 读取 + mock YouTube API + mock write_to_doris）
  - [x] 2.5 测试 URL 解析失败跳过（ValueError → warning，继续处理其他记录）
  - [x] 2.6 测试视频不存在跳过（API 返回空 items → warning，继续）
  - [x] 2.7 测试 API 配额超限（HTTP 403 → RuntimeError 抛出）

- [x] Task 3：更新 `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - [x] 3.1 `7-4-youtube视频统计数据采集落库` → `review`（dev 完成后 code-review 流程改为 done）

### Review Findings

- [x] [Review][Patch] `youtu.be/` 空路径和 `shorts/` 空 video_id — dismissed（两处均已有 `if vid:` 保护，fall through 到 ValueError，行为正确）
- [x] [Review][Patch] `item["id"]` 可能 KeyError [collectors/youtube_collector.py:227] — fixed: 改为 `item.get("id")` 并过滤空值
- [x] [Review][Patch] YOUTUBE_API_KEY 空白字符串通过校验 [collectors/youtube_collector.py:196] — fixed: 加 `.strip()`
- [x] [Review][Defer] API key 作为 query param 可能泄露 — deferred, pre-existing（与 sources/youtube.py 一致，YouTube Data API 标准用法）
- [x] [Review][Defer] SQL 表名拼接 [collectors/youtube_collector.py:101] — deferred, pre-existing（DINGTALK_CONTENT_TABLE 为模块级常量，非用户输入）
- [x] [Review][Defer] DB 连接失败无 try-except — deferred, pre-existing（与 dingtalk_collector.py 等既有 collector 模式一致）
- [x] [Review][Defer] 无 HTTP 重试逻辑 — deferred, pre-existing（与 awin_collector.py 一致）
- [x] [Review][Defer] `resp.json()` 未捕获 JSONDecodeError — deferred, pre-existing（与 awin_collector.py 一致）
- [x] [Review][Defer] `datetime.utcnow()` Python 3.12 废弃 — deferred, pre-existing（项目统一 naive UTC，Python 3.11 环境）
- [x] [Review][Defer] watermark 更新失败后数据已写入 — deferred, pre-existing（与 awin_collector.py 相同模式）

## Dev Notes

### 文件结构

```
bi/python_sdk/outdoor_collector/
└── collectors/
    └── youtube_collector.py          ← 本 Story 核心新建文件

outdoor-data-validator/
└── tests/
    └── test_youtube_collector.py     ← 单元测试（主仓库 tests/ 目录）
```

> `collectors/` 在 `bi/` submodule 内；测试文件在主仓库 `tests/`。
> `bi/` submodule 修改需单独在 `bi/` 内 commit，再在主仓库更新 submodule 引用。

### 关键约束：不得 import 主工具模块

```python
# ❌ 禁止
from sources.youtube import extract_video_id, fetch_video_stats
from config.credentials import get_credentials

# ✅ 正确：直接读取环境变量，复制所需函数逻辑
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.environ["YOUTUBE_API_KEY"]
```

`extract_video_id()` 逻辑需从 `sources/youtube.py` 复制到 collector 内（不 import），因为 `bi/` 是独立部署单元。

### 数据来源：从 Doris 读取钉钉 URL

Story 7.3 已将钉钉 `kol_tidwe_内容上线` 表写入 `hqware.ods_dingtalk_kol_tidwe_content`，列名含 `*` 前缀（反引号包裹）：

```python
import pymysql
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from doris_config import DorisConfig

def _fetch_urls_from_doris() -> list[dict]:
    """从 Doris 读取钉钉内容上线表的 record_id 和视频 URL。"""
    conn = DorisConfig().get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        "SELECT `record_id`, `*内容发布链接` AS url "
        "FROM hqware.ods_dingtalk_kol_tidwe_content "
        "WHERE `*内容发布链接` IS NOT NULL AND `*内容发布链接` != ''"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
```

> **注意**：列名 `*内容发布链接` 含 `*` 前缀，SQL 中必须用反引号包裹。

### YouTube API 批量调用（最多 50 个 video_id/次）

```python
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
HTTP_TIMEOUT = 30
BATCH_SIZE = 50  # YouTube API 单次最多 50 个 video_id

def _fetch_video_stats(video_ids: list[str], api_key: str) -> list[dict]:
    """批量获取 YouTube 视频统计数据。每批最多 50 个 video_id。"""
    all_items = []
    for i in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[i:i + BATCH_SIZE]
        resp = requests.get(
            f"{YOUTUBE_API_BASE}/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
                "key": api_key,
            },
            timeout=HTTP_TIMEOUT,
        )
        if resp.status_code == 403:
            raise RuntimeError(f"[{SOURCE}] YouTube API 配额超限（HTTP 403）")
        resp.raise_for_status()
        all_items.extend(resp.json().get("items", []))
    return all_items
```

### `extract_video_id()` 复制逻辑（来自 `sources/youtube.py`）

```python
from urllib.parse import urlparse, parse_qs

def _extract_video_id(url: str) -> str:
    """从 YouTube URL 提取 video_id。支持 watch?v=、youtu.be/、shorts/ 格式。"""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if hostname == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        if vid:
            return vid

    if hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            if vid:
                return vid
        if parsed.path.startswith("/shorts/"):
            vid = parsed.path.split("/shorts/", 1)[1].split("/")[0]
            if vid:
                return vid

    raise ValueError(f"[{SOURCE}] 无法从 URL 解析 video_id: {url}")

def _is_youtube_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in ("www.youtube.com", "youtube.com", "youtu.be")
```

### `_transform()` 字段映射

```python
def _transform(raw_items: list[dict], record_id_map: dict[str, str]) -> list[dict]:
    """将 YouTube API 响应映射为 Doris 格式。

    record_id_map: {video_id: dingtalk_record_id}
    """
    result = []
    now = datetime.utcnow()
    for item in raw_items:
        video_id = item.get("id", "")
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        result.append({
            "video_id":        video_id,
            "dingtalk_record_id": record_id_map.get(video_id),
            "title":           snippet.get("title", ""),
            "published_at":    snippet.get("publishedAt"),
            "duration":        content_details.get("duration"),  # ISO 8601，如 PT4M13S
            "view_count":      _to_int(stats.get("viewCount")),
            "like_count":      _to_int(stats.get("likeCount")),
            "comment_count":   _to_int(stats.get("commentCount")),
            "collected_at":    now,
        })
    return result

def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None
```

### `collect()` 主入口完整规范

```python
SOURCE = "youtube_collector"
TABLE  = "hqware.ods_youtube_video_stats"
UNIQUE_KEYS = ["video_id"]

def collect(dry_run: bool = False) -> int:
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        raise RuntimeError(f"[{SOURCE}] 未配置 YOUTUBE_API_KEY 环境变量")

    # 1. 从 Doris 读取钉钉 URL
    rows = _fetch_urls_from_doris()
    logger.info(f"[{SOURCE}] 从 Doris 读取 {len(rows)} 条钉钉记录")

    # 2. 过滤 YouTube URL，提取 video_id
    video_id_to_record_id: dict[str, str] = {}
    for row in rows:
        url = row.get("url") or ""
        if not _is_youtube_url(url):
            continue
        try:
            vid = _extract_video_id(url)
            video_id_to_record_id[vid] = row["record_id"]
        except ValueError as e:
            logger.warning(str(e))

    if not video_id_to_record_id:
        logger.info(f"[{SOURCE}] 无有效 YouTube URL，跳过采集")
        return 0

    logger.info(f"[{SOURCE}] 有效 YouTube video_id 数量：{len(video_id_to_record_id)}")

    # 3. 批量调用 YouTube API
    video_ids = list(video_id_to_record_id.keys())
    raw_items = _fetch_video_stats(video_ids, api_key)

    # 4. 处理 API 未返回的 video_id（视频已删除/私有）
    returned_ids = {item["id"] for item in raw_items}
    missing = set(video_ids) - returned_ids
    for vid in missing:
        logger.warning(f"[{SOURCE}] video_id={vid} 未在 API 返回中（视频可能已删除或私有），跳过")

    if not raw_items:
        logger.info(f"[{SOURCE}] YouTube API 返回空结果，跳过写入")
        return 0

    # 5. 转换并写入
    records = _transform(raw_items, video_id_to_record_id)

    if dry_run:
        logger.info(f"[{SOURCE}] dry-run，跳过写入，记录数={len(records)}")
        return 0

    written = write_to_doris(TABLE, records, UNIQUE_KEYS, source=SOURCE)
    update_watermark(SOURCE, "video_stats", datetime.utcnow())
    return written
```

### Doris 表结构（DDL 参考，由 DBA 建表，collector 不负责 DDL）

```sql
CREATE TABLE IF NOT EXISTS hqware.ods_youtube_video_stats (
    video_id            VARCHAR(64)    NOT NULL COMMENT 'YouTube 视频 ID（主键）',
    dingtalk_record_id  VARCHAR(64)    COMMENT '关联钉钉行 ID（来自 kol_tidwe_内容上线）',
    title               VARCHAR(512)   COMMENT '视频标题',
    published_at        VARCHAR(32)    COMMENT '发布时间（ISO 8601）',
    duration            VARCHAR(32)    COMMENT '视频时长（ISO 8601，如 PT4M13S）',
    view_count          BIGINT         COMMENT '播放数',
    like_count          BIGINT         COMMENT '点赞数（部分视频禁用则为 NULL）',
    comment_count       BIGINT         COMMENT '评论数',
    collected_at        DATETIME       NOT NULL COMMENT '采集时间（UTC）'
) UNIQUE KEY(video_id)
DISTRIBUTED BY HASH(video_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

### 凭证加载方式

`bi/` 内不使用 `config.credentials`（主仓库模块），直接读取环境变量：

```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.environ.get("YOUTUBE_API_KEY", "")
```

> `.env` 中对应键名为 `YOUTUBE_API_KEY`（已在 Phase 1 Story 1.2 中注册）。

### 单元测试规范 `tests/test_youtube_collector.py`

```python
import sys, os
sys.path.insert(0, "bi/python_sdk/outdoor_collector")
sys.path.insert(0, "bi/python_sdk/outdoor_collector/collectors")

from unittest.mock import patch, MagicMock
import pytest
import youtube_collector as yc

# 场景 1：_is_youtube_url 过滤
def test_is_youtube_url():
    assert yc._is_youtube_url("https://www.youtube.com/watch?v=abc") is True
    assert yc._is_youtube_url("https://youtu.be/abc") is True
    assert yc._is_youtube_url("https://www.instagram.com/p/abc") is False
    assert yc._is_youtube_url("") is False
    assert yc._is_youtube_url(None) is False

# 场景 2：extract_video_id 三种格式
def test_extract_video_id():
    assert yc._extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert yc._extract_video_id("https://youtu.be/abc123") == "abc123"
    assert yc._extract_video_id("https://www.youtube.com/shorts/abc123") == "abc123"
    with pytest.raises(ValueError):
        yc._extract_video_id("https://www.instagram.com/p/abc")

# 场景 3：_transform 字段映射
def test_transform():
    raw = [{
        "id": "vid1",
        "snippet": {"title": "Test Video", "publishedAt": "2026-01-01T00:00:00Z"},
        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
        "contentDetails": {"duration": "PT4M13S"},
    }]
    records = yc._transform(raw, {"vid1": "rec_001"})
    assert len(records) == 1
    r = records[0]
    assert r["video_id"] == "vid1"
    assert r["dingtalk_record_id"] == "rec_001"
    assert r["view_count"] == 1000
    assert r["like_count"] == 50
    assert r["comment_count"] == 10

# 场景 4：collect() 正常路径
@patch("youtube_collector._fetch_urls_from_doris")
@patch("youtube_collector._fetch_video_stats")
@patch("youtube_collector.write_to_doris", return_value=3)
@patch("youtube_collector.update_watermark")
def test_collect_normal(mock_wm, mock_write, mock_api, mock_doris):
    mock_doris.return_value = [
        {"record_id": "r1", "url": "https://www.youtube.com/watch?v=vid1"},
        {"record_id": "r2", "url": "https://www.instagram.com/p/abc"},  # 非 YouTube，跳过
    ]
    mock_api.return_value = [{
        "id": "vid1",
        "snippet": {"title": "T", "publishedAt": "2026-01-01T00:00:00Z"},
        "statistics": {"viewCount": "100", "likeCount": "5", "commentCount": "2"},
        "contentDetails": {"duration": "PT1M"},
    }]
    with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
        written = yc.collect()
    assert written == 3
    mock_write.assert_called_once()
    mock_wm.assert_called_once()

# 场景 5：URL 解析失败跳过（不中断）
@patch("youtube_collector._fetch_urls_from_doris")
@patch("youtube_collector._fetch_video_stats", return_value=[])
@patch("youtube_collector.write_to_doris", return_value=0)
@patch("youtube_collector.update_watermark")
def test_collect_invalid_url_skipped(mock_wm, mock_write, mock_api, mock_doris):
    mock_doris.return_value = [
        {"record_id": "r1", "url": "https://www.youtube.com/invalid_path"},
    ]
    with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
        written = yc.collect()
    assert written == 0  # 无有效 video_id，跳过

# 场景 6：API 配额超限 → RuntimeError
@patch("youtube_collector._fetch_urls_from_doris")
@patch("youtube_collector._fetch_video_stats",
       side_effect=RuntimeError("[youtube_collector] YouTube API 配额超限（HTTP 403）"))
def test_collect_quota_exceeded(mock_api, mock_doris):
    mock_doris.return_value = [
        {"record_id": "r1", "url": "https://www.youtube.com/watch?v=vid1"},
    ]
    with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_key"}):
        with pytest.raises(RuntimeError, match="配额超限"):
            yc.collect()
```

### 防回归约束

- **不修改** `sources/youtube.py`（Phase 1 成果，接口契约 authenticate/fetch_sample/extract_fields 保持不变）
- **不修改** `common/doris_writer.py`（Story 6.1 成果）
- **不修改** `common/watermark.py`（Story 6.2 成果）
- **不修改** `collectors/dingtalk_collector.py`（Story 7.3 成果）
- 主仓库 `tests/` 中已有的全部测试继续通过

### git submodule 操作说明

```bash
# 步骤 A：在 bi/ 内 commit
cd bi
git add python_sdk/outdoor_collector/collectors/youtube_collector.py
git commit --author="jiuyueshang <845126847@qq.com>" \
  -m "feat(outdoor_collector): Story 7.4 — YouTube 视频统计数据采集落库"

# 步骤 B：在主仓库 commit
cd ..
git add bi \
    tests/test_youtube_collector.py \
    _bmad-output/implementation-artifacts/7-4-youtube视频统计数据采集落库.md \
    _bmad-output/implementation-artifacts/sprint-status.yaml
git commit --author="jiuyueshang <845126847@qq.com>" \
  -m "feat(story-7.4): YouTube 视频统计数据采集落库 — done"
```

### 关键易错点（AI Agent 必读）

1. **列名含 `*` 前缀**：Doris 查询 `hqware.ods_dingtalk_kol_tidwe_content` 时，`*内容发布链接` 列名必须用反引号包裹：`` `*内容发布链接` ``

2. **不 import 主工具模块**：`extract_video_id` 逻辑需复制到 collector 内，不能 `from sources.youtube import ...`

3. **YouTube API 批量上限 50**：`_fetch_video_stats` 必须分批调用，每批最多 50 个 video_id

4. **likeCount 可能为 None**：部分视频禁用点赞数，API 不返回该字段，`_to_int(None)` 应返回 `None`，Doris 写 NULL

5. **视频已删除/私有**：API 不返回对应 item，需对比 video_ids 和 returned_ids，记录 warning 跳过，不报错

6. **水位线用途**：本 Story 水位线仅记录最近采集时间（`source="youtube_collector"`, `table="video_stats"`），无增量逻辑（每次全量刷新所有 URL）

7. **凭证不 import config.credentials**：`bi/` 模块使用 `os.environ.get()`，不引用主工具的 `config.credentials`

8. **DorisConfig 路径**：`sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))` 后可直接 `from doris_config import DorisConfig`

### 依赖已有文件（只读，不修改）

```
bi/python_sdk/outdoor_collector/common/watermark.py     ← get_watermark / update_watermark
bi/python_sdk/outdoor_collector/common/doris_writer.py  ← write_to_doris
bi/python_sdk/outdoor_collector/doris_config.py         ← DorisConfig 单例
sources/youtube.py                                       ← extract_video_id 逻辑参考（不 import）
```

### 现有 collectors 结构参考

```
bi/python_sdk/outdoor_collector/collectors/
├── __init__.py
├── awin_collector.py          ← 参考：sys.path 设置、水位线用法、write_to_doris 调用
├── dingtalk_collector.py      ← 参考：DorisConfig 读取、TABLE_CONFIG 模式
├── fb_collector.py
├── partnerboost_collector.py
├── tiktok_collector.py
└── tw_collector.py
```

### References

- [Source: epics.md#Story 7.4] — AC 定义、增量策略、依赖关系
- [Source: prd.md#FR41] — YouTube 采集功能需求
- [Source: architecture.md#Phase 2] — collector 架构规范、凭证加载方式
- [Source: implementation-artifacts/7-3-钉钉多维表数据采集落库.md] — Doris 表名、列名（含 `*` 前缀）、DorisConfig 用法
- [Source: implementation-artifacts/7-5-awin联盟数据采集落库.md] — collector 整体结构参考（sys.path、水位线、write_to_doris）
- [Source: sources/youtube.py] — extract_video_id 逻辑、YouTube API 端点、参数规范
- [Source: implementation-artifacts/6-1-目录初始化与公共写入工具.md] — write_to_doris() 签名
- [Source: implementation-artifacts/6-2-水位线管理器.md] — watermark API 规范

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

无

### Completion Notes List

- 实现 `bi/python_sdk/outdoor_collector/collectors/youtube_collector.py`：从 Doris 读取钉钉 URL → 过滤 YouTube → 批量调用 YouTube Data API v3（每批 50 个）→ upsert 写入 `hqware.ods_youtube_video_stats` → 更新水位线
- 所有函数均有类型注解，日志格式遵守 `[youtube_collector][table] 操作 ... 成功/失败`
- `_extract_video_id` 逻辑从 `sources/youtube.py` 复制，不 import 主工具模块
- 27 个单元测试全部通过，覆盖 7 个 AC 场景
- 回归测试：36 个 pre-existing 失败与本次改动无关，无新增回归

### File List

- `bi/python_sdk/outdoor_collector/collectors/youtube_collector.py`（新建）
- `tests/test_youtube_collector.py`（新建）
- `_bmad-output/implementation-artifacts/7-4-youtube视频统计数据采集落库.md`（更新）
- `_bmad-output/implementation-artifacts/sprint-status.yaml`（更新）
