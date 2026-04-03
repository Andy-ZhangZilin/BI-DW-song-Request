# Sprint Change Proposal
**日期：** 2026-04-03
**项目：** outdoor-data-validator
**变更范围分类：** Minor（可由开发团队直接实施）

---

## Section 1：问题摘要

**触发点：** Story 1.3（字段需求配置）执行前的工作流评估

**问题描述：**
原始计划中，工具运行产出 `{source}-raw.md` 报告后，由操作者本地人工对照《数据表需求》逐字段完成 `validation.md` 的填写。在实际执行评估中发现以下两个问题：

1. **字段需求配置内容不明确**：Story 1.3 的验收标准仅要求 `field_requirements.yaml` 包含"利润表至少 3 个示例字段"，缺乏完整的字段来源依据。现已明确来源文档为《指标梳理及数据需求沟通-2026.03.31.xlsx》，其"数据表需求"sheet 定义了完整的 11 张数据表及其字段清单。

2. **人工字段分析效率低下**：操作者本地无法高效完成多数据源 × 多报表的字段满足性论证，AI 辅助分析可显著提升效率和准确性。

**发现时间：** Sprint 执行前（Epic 1 开发中）

---

## Section 2：影响分析

### Epic 影响
- **Epic 1**（当前）：Story 1.1 和 Story 1.3 需要小范围调整，不影响 Epic 完成目标
- **Epic 2-5**：无影响，数据源接入和 CLI 实现不变

### Story 影响

| Story | 影响描述 |
|-------|---------|
| Story 1.1 - 项目结构初始化 | README 需新增 AI 辅助分析工作流步骤（第 4-5 步） |
| Story 1.3 - 字段需求配置 | field_requirements.yaml 内容范围从"示例字段"扩展到完整 11 张数据表 |
| 其余 Stories | 无影响 |

### Artifact 影响

| Artifact | 变更内容 |
|----------|---------|
| `_bmad-output/planning-artifacts/architecture.md` | ARCH8 分组键更新为 11 个明确组名 |
| `_bmad-output/planning-artifacts/epics.md` | Story 1.1 和 Story 1.3 验收标准更新 |
| 代码文件 | 无变更 |

### 技术影响
无代码层面变更，所有影响限于配置内容和文档范围。

---

## Section 3：推荐方案

**选择方案：直接调整（Direct Adjustment）**

在现有 Epic 1 内修改两个 Story 的验收标准，以及更新 ARCH8 架构决策描述。

**理由：**
- 变更范围极小，不影响任何功能实现逻辑
- 代码架构不变，仅配置内容和文档有更新
- 不增加 Sprint 工作量（field_requirements.yaml 本来就需要填写，只是明确了内容来源）

**工作量评估：** Low
**风险等级：** Low
**时间线影响：** 无

---

## Section 4：详细变更提案

### 变更 1：Story 1.3 验收标准更新

**Story：** 1.3 字段需求配置
**章节：** Acceptance Criteria

```
OLD（最后一条 AC）：
Given 初始 YAML 文件
When 查看内容
Then 包含利润表（profit_table）至少 3 个示例字段条目，每条含完整的三字段结构

NEW：
Given 初始 YAML 文件
When 查看内容
Then 包含以下全部 11 张数据表的字段需求，字段内容来源于
《指标梳理及数据需求沟通-2026.03.31.xlsx》"数据表需求"sheet：
  - profit_table（利润表）
  - financial_accounts_table（财务科目表）
  - marketing_performance_table（营销表现表）
  - dtc_ad_spend_table（DTC广告投放数据）
  - kol_info_table（KOL信息表）
  - kol_content_performance_table（KOL内容表现表）
  - kol_collaboration_table（KOL合作效果表）
  - tiktok_sales_table（TikTok销售分类表）
  - product_marketing_table（产品营销表现表）
  - social_media_account_table（社媒账号信息）
  - social_media_content_table（社媒发布内容信息）
每条记录均含完整三字段结构（display_name / source / table）
```

**理由：** 明确字段内容来源，确保工具输出的验证报告可覆盖全部业务报表需求

---

### 变更 2：ARCH8 架构决策更新

**Artifact：** architecture.md
**章节：** ARCH8

```
OLD（ARCH8）：
config/field_requirements.yaml 按报表分组（profit_table / marketing_table 等），
每条记录含 display_name、source、table 三字段

NEW（ARCH8）：
config/field_requirements.yaml 按数据表分组，分组键为以下 11 个（来源：《指标梳理及数据需求沟通》）：
profit_table / financial_accounts_table / marketing_performance_table /
dtc_ad_spend_table / kol_info_table / kol_content_performance_table /
kol_collaboration_table / tiktok_sales_table / product_marketing_table /
social_media_account_table / social_media_content_table
每条记录含 display_name（中文字段名）、source（数据源模块名）、table（端点/表名）三字段
```

**理由：** 消除架构描述中的模糊占位符，与实际业务需求对齐

---

### 变更 3：Story 1.1 README 更新

**Story：** 1.1 项目结构初始化
**章节：** Acceptance Criteria（README 内容要求）

```
OLD：
README 包含：环境要求、pip install 命令、playwright install 说明、
各数据源运行命令示例

NEW（追加步骤说明）：
README 包含（在运行命令示例后）：
## 字段分析工作流
运行完成后，获取 reports/{source}-raw.md，按以下步骤完成字段满足性分析：
1. 将 raw.md 内容提交给 AI 助手（Capy/Claude）
2. 请求分析：该数据源字段是否满足 config/field_requirements.yaml 中对应表的需求
3. 根据 AI 分析结论，填写或确认 reports/{source}-validation.md
4. 11 张数据表与数据源的对应关系见 config/field_requirements.yaml
```

**理由：** 明确工具交付后的操作流程，确保可交接性

---

## Section 5：实施交接

**变更范围分类：** Minor — 可由开发团队直接实施

**执行方：** 开发团队（Amelia / 开发 Agent）

**实施任务清单：**
- [ ] 更新 `epics.md` 中 Story 1.3 的最后一条 AC
- [ ] 更新 `epics.md` 中 Story 1.1 的 README AC
- [ ] 更新 `architecture.md` 中的 ARCH8 描述
- [ ] Story 1.3 开发时，按 11 张表完整填充 `field_requirements.yaml`

**成功标准：**
- `field_requirements.yaml` 包含全部 11 张数据表的字段条目
- `reports/{source}-raw.md` 包含需求字段对照区块，字段来自上述 11 个分组
- README 中有明确的 AI 辅助分析步骤说明
