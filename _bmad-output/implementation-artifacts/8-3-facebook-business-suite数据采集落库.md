# Story 8.3：Facebook Business Suite 社媒数据采集落库

Status: done

## Story

作为数据工程师，
我希望能将 Facebook Business Suite 的帖子/Reels 数据采集并写入 Doris，
以便构建社媒内容表现报表。

## Acceptance Criteria

1. 采用 Playwright 登录 Meta Business Suite，抓取帖子和 Reels 列表（`sync_playwright`，禁止 async 版本）
2. 增量策略：全量拉取 + upsert（UI 时间筛选稳定性待验证后可扩展增量）
3. 写入字段：帖子 ID、标题、发布日期、状态、覆盖人数、获赞数、评论数、分享次数（共 8 个）
4. 写入策略：upsert，以帖子 ID 为主键，确保幂等写入
5. 遇验证码时抛出 `RuntimeError`，不静默失败
6. collector 脚本位于 `bi/python_sdk/outdoor_collector/collectors/fb_collector.py`
7. 依赖 Story 6.1 的 `common/doris_writer.py` 写入封装（本 Story 须先实现 6.1 的依赖代码）

## Tasks / Subtasks

### 前置：实现 Story 6.1 依赖代码（AC: #6 #7）

- [ ] Task 0：创建 outdoor_collector/ 目录结构（Story 6.1 依赖，8.3 所需）
  - [ ] 0.1 创建 `bi/python_sdk/outdoor_collector/__init__.py`
  - [ ] 0.2 创建 `bi/python_sdk/outdoor_collector/common/__init__.py`
  - [ ] 0.3 创建 `bi/python_sdk/outdoor_collector/collectors/__init__.py`
  - [ ] 0.4 复制 doris_config.py 到 `bi/python_sdk/outdoor_collector/doris_config.py`（沿用单例模式）
  - [ ] 0.5 创建 `bi/python_sdk/outdoor_collector/requirements.txt`（含 requests、pymysql、playwright、python-dotenv）

- [ ] Task 1：实现 `common/doris_writer.py`（Story 6.1 AC，AC: #7）
  - [ ] 1.1 实现 `write_to_doris(table: str, records: list[dict], unique_keys: list[str]) -> int`
    - 内部使用 pymysql + executemany，batch_size=1000
    - 写入前执行 `SET enable_unique_key_partial_update = true` 和 `SET enable_insert_strict = false`
    - 日志格式：`[{source}][{table}] 写入 {n} 行 ... 成功/失败`
    - 返回写入行数

### 主体：实现 fb_collector.py（AC: #1-#6）

- [ ] Task 2：实现帖子 ID 提取逻辑（AC: #3 #4）
  - [ ] 2.1 在抓取帖子行时同步提取帖子 ID（href 链接中的数字 ID 或 data-attribute）
  - [ ] 2.2 帖子 ID 提取策略：优先从行内链接 href 解析（如 `permalink/123456789/`），无法解析时生成 `date_hash` 替代键

- [ ] Task 3：实现 `collectors/fb_collector.py`（AC: #1 #2 #4 #5 #6）
  - [ ] 3.1 实现 `collect()` 主函数：Playwright 登录 + 抓取 + 写入 Doris
    - 复用 `sources/social_media.py` 的登录逻辑（`_login`、session 持久化）
    - **不得 import** 主工具模块（`validate`、`reporter`、`sources.*`、`config.credentials`）
    - 凭证通过 `python-dotenv` 直接从 `.env` 加载（`os.getenv`）
    - 导航至 `https://business.facebook.com/latest/posts/published_posts`
    - 调用增强版行提取（含帖子 ID），返回 list[dict]
    - 调用 `write_to_doris` 写入 Doris
  - [ ] 3.2 遇验证码时抛出 `RuntimeError`，不静默失败（AC: #5）
  - [ ] 3.3 实现命令行入口：`python fb_collector.py`，支持 `--dry-run` 参数（打印数据但不写入 Doris）

- [ ] Task 4：Doris 表建表语句（AC: #3 #4）
  - [ ] 4.1 在 Dev Notes 中提供 `outdoor_collector_facebook_posts` 建表 DDL
  - [ ] 4.2 确认主键为 `post_id`，使用 Unique Key 模型

- [ ] Task 5：集成验证
  - [ ] 5.1 `--dry-run` 模式验证：输出抓取结果不写入 Doris
  - [ ] 5.2 验证字段完整性：8 个字段均正确写入

## Dev Notes

### 关键架构约束

**代码位置（绝对路径）：**
```
bi/python_sdk/outdoor_collector/
├── __init__.py                    ← Task 0 创建
├── doris_config.py                ← Task 0 复制（不改动单例逻辑）
├── requirements.txt               ← Task 0 创建
├── sdk/                           ← Story 6.0 已完成，不动
├── common/
│   ├── __init__.py                ← Task 0 创建
│   └── doris_writer.py            ← Task 1 实现（Story 6.1 核心产物）
└── collectors/
    ├── __init__.py                ← Task 0 创建
    └── fb_collector.py            ← Task 3 实现（本 Story 核心产物）
```

**与 Phase 1 代码的隔离（关键！）：**
- `outdoor_collector/` 是独立部署单元，**禁止 import** 主工具模块
- 凭证加载：直接使用 `python-dotenv` + `os.getenv()`，**不用** `config.credentials.get_credentials()`
- 报告写入：不调用 `reporter.py`，直接写入 Doris

### doris_config.py 单例模式（Task 0 必读）

复制现有 `bi/python_sdk/doris_config.py`，路径改为 `outdoor_collector/doris_config.py`。单例模式如下（勿重复实例化）：

```python
# outdoor_collector/doris_config.py  —— 复制自 bi/python_sdk/doris_config.py，单例模式不变
class DorisConfig:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # ... 连接初始化
        return cls._instance
```

**禁止 `DorisConfig()` 在每个函数中重复实例化，全局共享同一连接。**

### common/doris_writer.py 实现规范（Task 1）

```python
import logging
import pymysql
from typing import Any
from .doris_config import DorisConfig  # 注意：相对导入路径

# 注意：从 outdoor_collector 包级别导入
from outdoor_collector.doris_config import DorisConfig

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

def write_to_doris(table: str, records: list[dict], unique_keys: list[str], source: str = "collector") -> int:
    """
    将 records 批量 upsert 写入 Doris 指定表。

    Args:
        table: 目标 Doris 表名（含库名，如 "hqware.outdoor_collector_facebook_posts"）
        records: 待写入记录列表，每项为 {列名: 值} 字典
        unique_keys: 主键列名列表（用于 upsert 去重，不影响 INSERT 语句）
        source: 日志来源标识（默认 "collector"）

    Returns:
        实际写入行数

    Raises:
        RuntimeError: Doris 写入失败时抛出，不静默失败
    """
    if not records:
        logger.info(f"[{source}][{table}] 无数据写入，跳过")
        return 0

    config = DorisConfig()
    conn = config.get_connection()  # 或 config.connection，取决于实际 DorisConfig 接口

    columns = list(records[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(f"`{c}`" for c in columns)
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

    total = 0
    try:
        cursor = conn.cursor()
        # Doris upsert 前置 SET
        cursor.execute("SET enable_unique_key_partial_update = true")
        cursor.execute("SET enable_insert_strict = false")

        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            values = [[r.get(c) for c in columns] for r in batch]
            cursor.executemany(sql, values)
            conn.commit()
            total += len(batch)
            logger.info(f"[{source}][{table}] 写入 {total}/{len(records)} 行 ... 进行中")

        logger.info(f"[{source}][{table}] 写入 {total} 行 ... 成功")
        return total
    except Exception as e:
        logger.error(f"[{source}][{table}] 写入 {total} 行 ... 失败：{e}")
        raise RuntimeError(f"[{source}][{table}] Doris 写入失败：{e}") from e
```

**重要：先读 `bi/python_sdk/doris_config.py` 确认 `DorisConfig` 的连接获取接口（`get_connection()` 或 `connection` 属性），再编写 `write_to_doris`，不能猜测接口！**

### fb_collector.py 核心实现（Task 3）

**凭证加载（outdoor_collector 独立，不用 config.credentials）：**
```python
from dotenv import load_dotenv
import os

load_dotenv()

FACEBOOK_USERNAME = os.getenv("FACEBOOK_USERNAME")
FACEBOOK_PASSWORD = os.getenv("FACEBOOK_PASSWORD")
```

**登录与 Session 复用（从 sources/social_media.py 移植逻辑，不直接 import）：**
- Session 文件路径：`~/.sessions/facebook_collector_state.json`（避免与 Phase 1 工具的 `.sessions/facebook_state.json` 冲突）
- 复用 `_login()` 的两步登录逻辑（路径 A：页面内直接输入；路径 B：popup 弹窗）
- PAGE_WAIT_TIMEOUT_MS = 60_000（与 social_media.py 实际超时一致）
- TOTAL_TIMEOUT_S = 300（采集场景允许更长时间）

**帖子 ID 提取策略（Task 2，关键！）：**

页面帖子行通常包含指向帖子详情页的链接，URL 格式为：
`https://www.facebook.com/permalink.php?story_fbid=123456789`
或 `/posts/123456789/`

提取逻辑（在 `_extract_post_rows_with_id()` 中实现）：
```python
# 在已有的 table/ARIA 行提取基础上，额外提取帖子 ID
def _extract_post_id_from_row(row_el) -> str | None:
    """从行元素中提取帖子 ID（从链接 href 解析）。"""
    try:
        links = row_el.query_selector_all("a[href*='post']")
        for link in links:
            href = link.get_attribute("href") or ""
            # 尝试从 URL 中提取数字 ID
            import re
            match = re.search(r'/(?:posts|permalink(?:\.php\?story_fbid=)?)/?(\d+)', href)
            if match:
                return match.group(1)
        # 备选：从 data-id 属性提取
        data_id = row_el.get_attribute("data-id") or row_el.get_attribute("data-post-id")
        return data_id
    except Exception:
        return None
```

**无法提取帖子 ID 时的降级策略：**
- 使用 `{发布日期}_{标题[:20]}` 的 md5 hash 作为伪 ID
- 记录 warning 日志，不阻断采集

**Doris 写入字段映射：**
```python
DB_FIELD_MAP = {
    "post_id":     "post_id",        # 帖子 ID（从链接提取）
    "title":       "标题",
    "publish_date": "发布日期",
    "status":      "状态",
    "reach":       "覆盖人数",
    "likes":       "获赞数和心情数",
    "comments":    "评论数",
    "shares":      "分享次数",
    "collected_at": None,             # 采集时间，由程序自动填充 datetime.now()
}
```

### Doris 建表 DDL（Task 4）

```sql
-- 数据库：hqware（与现有业务表同库）
CREATE TABLE IF NOT EXISTS hqware.outdoor_collector_facebook_posts (
    `post_id`      VARCHAR(200)   NOT NULL COMMENT '帖子ID（从页面链接提取）',
    `title`        VARCHAR(1000)  NULL     COMMENT '帖子标题',
    `publish_date` VARCHAR(50)    NULL     COMMENT '发布日期（原始文本，如"4月7日 21:30"）',
    `status`       VARCHAR(50)    NULL     COMMENT '帖子状态（如"已发布"）',
    `reach`        BIGINT         NULL     COMMENT '覆盖人数',
    `likes`        BIGINT         NULL     COMMENT '获赞数和心情数',
    `comments`     BIGINT         NULL     COMMENT '评论数',
    `shares`       BIGINT         NULL     COMMENT '分享次数',
    `collected_at` DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间'
) UNIQUE KEY(`post_id`)
DISTRIBUTED BY HASH(`post_id`) BUCKETS 4
PROPERTIES (
    "replication_num" = "1"
);
```

**注意：** 表名用 `outdoor_collector_facebook_posts`，保持与 Phase 2 其他表命名风格一致。若数据库名不是 `hqware`，请核对现有 `doris_config.py` 中的 `database` 配置。

### 数值字段清洗（Task 3）

Facebook 页面中数值可能含逗号（如 `"1,234"`）或中文单位（如 `"1.2万"`），写入 Doris BIGINT 前需清洗：

```python
def _parse_int(value: str | None) -> int | None:
    """将页面文本数值转换为整数（处理逗号分隔、万/千单位）。"""
    if value is None or value == "--":
        return None
    s = str(value).replace(",", "").replace(" ", "")
    # 处理中文单位
    multiplier = 1
    if s.endswith("万"):
        multiplier = 10000
        s = s[:-1]
    elif s.endswith("千"):
        multiplier = 1000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except (ValueError, TypeError):
        return None
```

### fb_collector.py 完整骨架

```python
"""
Facebook Business Suite 社媒数据采集脚本（Story 8.3）。

用法：
    cd bi/python_sdk/outdoor_collector
    python collectors/fb_collector.py              # 正式写入 Doris
    python collectors/fb_collector.py --dry-run    # 仅抓取，不写入

前置：.env 文件需含 FACEBOOK_USERNAME / FACEBOOK_PASSWORD
依赖：Story 6.0（sdk/），Story 6.1（common/doris_writer.py，本 Story 同步实现）
"""
import argparse
import hashlib
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    sync_playwright = None
    PlaywrightTimeoutError = Exception

# 项目内导入（相对导入）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.doris_writer import write_to_doris

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---- 常量 ----
FB_LOGIN_URL = "https://business.facebook.com/business/loginpage"
POSTS_URL = "https://business.facebook.com/latest/posts/published_posts"
PAGE_WAIT_TIMEOUT_MS = 60_000
TOTAL_TIMEOUT_S = 300
MAX_ROWS = 200
SESSION_FILE = Path.home() / ".sessions" / "facebook_collector_state.json"
DORIS_TABLE = "hqware.outdoor_collector_facebook_posts"

TARGET_FIELDS = ["标题", "发布日期", "状态", "覆盖人数", "获赞数和心情数", "评论数", "分享次数"]
CAPTCHA_KEYWORDS = ["captcha", "verify you are human", "robot", "验证码", "security check", "confirm your identity"]


def collect(dry_run: bool = False) -> int:
    """主采集函数。返回写入行数（dry_run 时返回抓取行数）。"""
    username = os.getenv("FACEBOOK_USERNAME")
    password = os.getenv("FACEBOOK_PASSWORD")
    if not username or not password:
        raise RuntimeError("[fb_collector] 缺少凭证：FACEBOOK_USERNAME 或 FACEBOOK_PASSWORD 未配置")

    records = _scrape_posts(username, password)
    logger.info(f"[fb_collector][facebook_posts] 抓取 {len(records)} 条记录")

    if dry_run:
        logger.info("[fb_collector] dry-run 模式，跳过写入")
        for r in records[:5]:
            logger.info(f"  {r}")
        return len(records)

    return write_to_doris(DORIS_TABLE, records, ["post_id"], source="fb_collector")


def _scrape_posts(username: str, password: str) -> list[dict]:
    """登录 Facebook Business Suite 并抓取帖子数据。"""
    # ... 实现参考 sources/social_media.py，含 session 复用 + _login() 两步登录
    ...


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook Business Suite 采集脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取，不写入 Doris")
    args = parser.parse_args()
    count = collect(dry_run=args.dry_run)
    logger.info(f"[fb_collector] 完成，共处理 {count} 条")
```

### 文件命名与路径规范（project-context.md 规范）

- 文件：`snake_case`（`fb_collector.py`、`doris_writer.py`）
- 类：`PascalCase`（如需）
- 常量：`UPPER_SNAKE_CASE`
- 私有函数：单下划线前缀（`_scrape_posts`、`_extract_post_rows_with_id`、`_parse_int`、`_check_captcha`、`_login`）
- 日志格式：`[fb_collector][{table}] 操作描述 ... 成功/失败`

### DorisConfig 接口确认（实现前必查）

**先读 `bi/python_sdk/doris_config.py` 源码**，确认以下接口：
- 连接获取方式（`DorisConfig().connection` 还是 `DorisConfig().get_connection()`）
- 数据库名（`database` 字段，用于核对 `DORIS_TABLE` 前缀）
- commit 方式（auto-commit 还是手动 commit）

### 禁止行为

- ❌ 在 `outdoor_collector/` 中 import `sources.*`、`config.credentials`、`reporter`、`validate`
- ❌ 直接在 collector 中调用 `get_credentials()`（Phase 1 凭证加载器）
- ❌ 使用 `async_playwright`，必须用 `sync_playwright`
- ❌ 静默忽略验证码，必须抛出 `RuntimeError`
- ❌ 重复实例化 `DorisConfig()`，全局共享单例

### Project Structure Notes

**新增/修改文件清单：**

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `bi/python_sdk/outdoor_collector/__init__.py` | 新增 | 空文件 |
| `bi/python_sdk/outdoor_collector/doris_config.py` | 新增 | 从 `bi/python_sdk/doris_config.py` 复制 |
| `bi/python_sdk/outdoor_collector/requirements.txt` | 新增 | requests、pymysql、playwright、python-dotenv |
| `bi/python_sdk/outdoor_collector/common/__init__.py` | 新增 | 空文件 |
| `bi/python_sdk/outdoor_collector/common/doris_writer.py` | 新增 | Story 6.1 写入封装 |
| `bi/python_sdk/outdoor_collector/collectors/__init__.py` | 新增 | 空文件 |
| `bi/python_sdk/outdoor_collector/collectors/fb_collector.py` | 新增 | Story 8.3 主体 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | 修改 | 8-3 → in-progress（dev-story 时更新） |

**不修改的文件：**
- `sources/social_media.py`：仅作参考，不修改，不 import
- `bi/python_sdk/outdoor_collector/sdk/`：Story 6.0 已完成，不动
- 主工具所有文件（validate.py、reporter.py 等）

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.3] — 验收标准、写入字段
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1] — 目录结构、doris_writer 规范
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-15.md#目录结构] — outdoor_collector/ 完整结构
- [Source: sources/social_media.py] — 登录逻辑、session 持久化、帖子行提取（参考，不 import）
- [Source: _bmad-output/implementation-artifacts/6-0-api客户端sdk层建立.md#Dev Notes] — DorisConfig 单例模式、凭证加载方式
- [Source: _bmad-output/project-context.md] — 命名规范、bi/ 子模块代码规范
- [Source: bi/python_sdk/doris_config.py] — 在实现前必须读取，确认 DorisConfig 接口

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

### Review Findings

- [x] [Review][Decision] Reels 未实现 — dismissed：Facebook Business Suite published_posts 页面将 Reels 与普通帖子放在同一列表，当前实现已覆盖；且当前环境 Facebook 不通，无法验证，暂不单独实现
- [x] [Review][Patch] Login popup path B 轮询检查 page.url 而非 popup.url — 已修复：path B 完成后等待 popup 跳转出 login，再主动导航主页面 [fb_collector.py:_login()]
- [x] [Review][Patch] HTML table 分支无 cell 索引越界保护 — 原代码已有 `i < len(cells)` 保护，无需额外修改 [fb_collector.py:_extract_post_rows_with_id()]
- [x] [Review][Patch] 表头存在但 TARGET_FIELDS 无匹配时静默返回空结果 — 已修复：添加 warning 日志 [fb_collector.py:_extract_post_rows_with_id()]
- [x] [Review][Patch] _check_captcha 对 page.evaluate 异常静默 return — 已修复：改为 warning 日志记录 [fb_collector.py:_check_captcha()]
- [x] [Review][Patch] sync_playwright=None 时错误信息无用 — 已修复：ImportError 时立即抛出含安装指引的错误 [fb_collector.py:import区]
- [x] [Review][Patch] collect 过滤条件应为 is not None — 已修复 [fb_collector.py:collect()]
- [x] [Review][Patch] MAX_ROWS=200 触碰上限时静默截断 — 已修复：两个分支均添加 warning 日志 [fb_collector.py:_extract_post_rows_with_id()]
- [x] [Review][Defer] Fallback post_id MD5 碰撞风险：同标题+日期的两条帖子 hash 相同，Doris upsert 覆盖一条 [fb_collector.py:_fallback_id()] — deferred, 采集场景内容碰撞极低概率，后续可改为更强 hash 或用 URL hash
- [x] [Review][Defer] _login() 路径 A/B 各有 time.sleep(15) 硬编码等待，浪费时间预算 [fb_collector.py:_login()] — deferred, 与参考实现 social_media.py 保持一致，后续优化
- [x] [Review][Defer] SESSION_FILE 目录创建无 mode=0o700，在多用户机器上 session 文件可被他人读取 [fb_collector.py:_save_session()] — deferred, 生产环境单用户部署，暂不处理
- [x] [Review][Defer] page.type() 逐键入密码，若开启 Playwright 追踪则密码明文记录 [fb_collector.py:_login()] — deferred, 未启用追踪，后续可改为 page.fill()
- [x] [Review][Defer] _try_session() 中 time.sleep(5) 硬编码，慢网络可能 session 未完全写入 [fb_collector.py:_try_session()] — deferred, 与参考实现一致
- [x] [Review][Defer] 正则 \d{10,} 排除短数字 ID，老帖子/历史内容可能触发降级 fallback [fb_collector.py:_extract_post_id_from_element()] — deferred, 10位以上覆盖当前 Facebook ID 格式
