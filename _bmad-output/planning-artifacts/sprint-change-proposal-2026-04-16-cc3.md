# Sprint Change Proposal - 2026-04-16 (CC#3)

**生成时间：** 2026-04-16  
**变更类型：** 范围调整（Scope Adjustment）  
**影响 Epic：** Epic 7（API 类数据源采集落库）  
**影响 Story：** 7-2（TikTok Shop 数据采集落库）  
**变更范围：** Moderate

---

## Part 1：问题陈述

### 触发背景

在 Phase 2 数据采集落库的测试阶段（2026-04-16），发现 Story 7-2 的 TikTok collector 实现与实际验证结果存在偏差。

### 核心问题

**Story 7-2 当前实现了 6 个 TikTok 接口路由，但验证报告显示只有 4 个接口返回有效数据：**

| 接口 | 验证状态 | Collector 状态 | 数据行数 |
|------|---------|---------------|---------|
| `return_refund` | ✅ 已生成 | ✅ 已实现 | 50 |
| `video_performances` | ✅ 已生成 | ✅ 已实现 | 20 |
| `shop_product_performance` | ✅ 已生成 | ✅ 已实现 | 23 |
| `shop_video_performance_detail` | ✅ 已生成 | ❌ **缺失** | 28 |
| `affiliate_creator_orders` | ❌ 未验证 | ✅ 已实现 | 0 |
| `affiliate_campaign_performance` | ❌ 0条 | ✅ 已实现 | 0 |
| `affiliate_sample_status` | ❌ 0条 | ✅ 已实现 | 0 |

**具体问题：**
1. **缺失接口：** `shop_video_performance_detail` 在验证报告中有 28 个字段和真实数据，但 collector 完全没有实现
2. **无效接口：** `affiliate_campaign_performance` 和 `affiliate_sample_status` 返回 0 条数据，写入 Doris 无意义
3. **未验证接口：** `affiliate_creator_orders` 从未出现在验证报告中，未知是否可通

### 发现方式

- 对比 `all-sources-aggregate.md`（验证结果汇总）与 `tiktok_collector.py`（实现代码）
- 验证报告来源：`reports/tiktok-raw.md`（2026-04-10 生成）

---

## Part 2：影响分析

### Epic 影响

**Epic 7（API 类数据源采集落库）**
- 当前状态：in-progress
- 受影响 Story：7-2
- 其他 Story（7-1, 7-3, 7-4, 7-5）：无影响

### Story 影响

**Story 7-2：TikTok Shop 数据采集落库**

| 项目 | 当前 | 修改后 | 影响 |
|------|------|--------|------|
| 路由数量 | 6 个 | 4 个 | 减少 2 个无效路由，新增 1 个缺失路由 |
| 采集函数 | 6 个 | 4 个 | 移除 3 个，新增 1 个 |
| Doris 表 | 6 张 | 4 张 | 对应 4 个有数据的路由 |
| 验收标准 | AC#2 提及 6 个路由 | AC#2 改为 4 个路由 | 与实际可用接口对齐 |
| 状态 | done | in-progress | 需要实现新函数和补充测试 |

### 工件影响

| 工件 | 修改类型 | 影响范围 |
|------|---------|---------|
| `7-2-tiktok-shop数据采集落库.md` | 更新 AC 和 Tasks | 验收标准、任务清单、DDL |
| `tiktok_collector.py` | 代码修改 | ROUTES 配置、函数定义、路由调用 |
| `test_tiktok_collector.py` | 测试修改 | mock 数据、测试用例 |
| `sprint-status.yaml` | 状态更新 | 7-2 从 done 改为 in-progress |

### PRD 和 Architecture 影响

✅ **无冲突**
- PRD 中对 TikTok 的需求为"采集 TikTok Shop 的订单、商品、视频及联盟数据"，未指定具体接口数量
- Architecture 文档中的 TikTok 规范（ARCH5）不涉及具体接口列表

---

## Part 3：推荐方案

### 选项评估

**选项 1：直接调整** ✅ **推荐**
- 修改 Story 7-2 的 AC 和实现
- 移除 3 个无数据的路由，新增 1 个有数据的路由
- 工作量：低（2-3 小时）
- 风险：低
- 时间影响：无（可在当前 sprint 内完成）

**选项 2：回滚重新实现** ❌ 不推荐
- 工作量：高（6-8 小时）
- 风险：中（可能引入新 bug）
- 时间影响：负面（延迟 1-2 天）

**选项 3：调整 MVP 范围** ❌ 不推荐
- 影响业务价值（TikTok 是核心数据源）
- 无法解决根本问题

### 推荐理由

1. **最小化工作量：** 只需调整路由配置和补充 1 个函数
2. **快速恢复一致性：** 与验证报告对齐，为后续测试做准备
3. **无时间延迟：** 可在当前 sprint 内完成
4. **低风险：** 范围调整，无新技术风险

---

## Part 4：具体变更提案

### 提案 1：更新 Story 7-2 验收标准

**文件：** `_bmad-output/implementation-artifacts/7-2-tiktok-shop数据采集落库.md`

**AC#2 修改：**
```
OLD: 采集 6 个路由：return_refund、affiliate_creator_orders、video_performances、
     shop_product_performance、affiliate_campaign_performance、affiliate_sample_status

NEW: 采集 4 个路由：return_refund、video_performances、shop_product_performance、
     shop_video_performance_detail
```

---

### 提案 2：更新 Story 7-2 Tasks

**文件：** `_bmad-output/implementation-artifacts/7-2-tiktok-shop数据采集落库.md`

**Task 1 修改：**
- 移除 Task 1.4（affiliate_creator_orders）
- 移除 Task 1.7（affiliate_campaign_performance）
- 移除 Task 1.8（affiliate_sample_status）
- 新增 Task 1.7（shop_video_performance_detail）

---

### 提案 3：补充 shop_video_performance_detail DDL

**文件：** `_bmad-output/implementation-artifacts/7-2-tiktok-shop数据采集落库.md`

**新增 DDL：**
```sql
CREATE TABLE IF NOT EXISTS hqware.ods_tiktok_shop_video_performance_detail (
    video_id        VARCHAR(64)   NOT NULL COMMENT '视频 ID',
    collect_date    DATE          NOT NULL COMMENT '采集日期',
    latest_available_date VARCHAR(50) COMMENT '最新可用日期',
    likes           BIGINT        COMMENT '点赞数',
    comments        BIGINT        COMMENT '评论数',
    shares          BIGINT        COMMENT '分享数',
    views           BIGINT        COMMENT '浏览数',
    customers       BIGINT        COMMENT '客户数',
    gmv_amount      DECIMAL(18,4) COMMENT 'GMV 金额',
    gmv_currency    VARCHAR(10)   COMMENT 'GMV 货币',
    raw_json        TEXT          COMMENT '原始响应',
    collected_at    DATETIME DEFAULT NOW()
) UNIQUE KEY(video_id, collect_date)
DISTRIBUTED BY HASH(video_id) BUCKETS 4
PROPERTIES ("replication_num" = "1");
```

---

### 提案 4：更新 tiktok_collector.py

**文件：** `bi/python_sdk/outdoor_collector/collectors/tiktok_collector.py`

**修改内容：**
1. 更新 ROUTES 配置：移除 3 个路由，保留 4 个
2. 移除 3 个采集函数：`_collect_affiliate_creator_orders()`、`_collect_affiliate_campaign_performance()`、`_collect_affiliate_sample_status()`
3. 新增 1 个采集函数：`_collect_shop_video_performance_detail()`
4. 更新 `collect()` 函数中的路由分支

---

### 提案 5：更新 sprint-status.yaml

**文件：** `_bmad-output/implementation-artifacts/sprint-status.yaml`

**修改内容：**
```yaml
# CC 2026-04-16: 7-2 范围调整 - 移除 3 个无数据路由，新增 1 个有数据路由
7-2-tiktok-shop数据采集落库: in-progress
```

---

## Part 5：实施交接

### 变更范围分类

**Moderate（中等范围）**
- 需要修改已完成的 Story 7-2
- 涉及代码修改、测试更新、文档更新
- 可在当前 sprint 内完成

### 交接对象

**开发团队（Dev Agent）**
- 实现 `_collect_shop_video_performance_detail()` 函数
- 移除 3 个无效函数
- 更新 ROUTES 配置
- 更新测试用例

**Scrum Master**
- 更新 Story 7-2 的 AC 和 Tasks
- 更新 sprint-status.yaml
- 记录变更原因

### 成功标准

1. ✅ `_collect_shop_video_performance_detail()` 实现完成
2. ✅ 3 个无效函数已移除
3. ✅ ROUTES 配置已更新为 4 个路由
4. ✅ 所有测试用例已更新并通过
5. ✅ Story 7-2 的 AC 和 Tasks 已更新
6. ✅ sprint-status.yaml 已更新

### 时间估计

- 实现新函数：1 小时
- 移除旧函数和更新配置：0.5 小时
- 更新测试：0.5 小时
- 文档更新：0.5 小时
- **总计：2.5 小时**

### 依赖和风险

**依赖：**
- 无新的外部依赖
- 依赖现有的 TikTokClient 和 write_to_doris 接口

**风险：**
- 低风险：只是调整现有实现，无新技术引入
- 缓解措施：充分的单元测试覆盖

---

## Part 6：后续行动

### 立即行动

1. 获取用户批准（本提案）
2. 将 Story 7-2 标记为 in-progress
3. 分配开发任务给开发团队

### 实施步骤

1. 实现 `_collect_shop_video_performance_detail()` 函数
2. 移除 3 个无效函数
3. 更新 ROUTES 配置
4. 更新测试用例
5. 更新 Story 7-2 文档
6. 更新 sprint-status.yaml
7. 运行 `--dry-run` 验证采集逻辑
8. 标记 Story 7-2 为 done

### 验证方式

```bash
# 验证 4 个路由都能采集
python collectors/tiktok_collector.py --dry-run

# 验证测试通过
pytest tests/test_tiktok_collector.py -v
```

---

**变更提案生成完成。** 等待用户批准。
