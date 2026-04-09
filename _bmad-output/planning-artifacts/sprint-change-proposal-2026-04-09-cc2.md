# Sprint Change Proposal — 2026-04-09 CC#2

## 1. 问题摘要

**触发来源：** 报告体系需求变更（用户发起 BMAD CC 流程）

**问题描述：** 原有报告体系存在以下问题需要重构：
- raw 报告中的"需求字段（待人工对照）"区块实用性低，人工对照效率不佳
- `{source}-validation.md` 双文件策略过于复杂，人工维护成本高
- 缺少全局视角的聚合分析能力，无法一次性看到所有数据源与 11 张报表的映射关系
- `field_requirements.yaml` 结构过旧，不匹配最新 11 张报表定义

**变更决定：** 废弃人工对照工作流，转向 AI 驱动的字段映射分析。

---

## 2. 变更清单

### 变更 A：移除 raw 报告中的需求字段对照区块

- `reporter.py` 的 `_render_raw_report()` 不再渲染"需求字段（待人工对照）"section
- 移除内部函数 `_get_source_requirements()` 和 `_render_validation_template()`
- raw 报告仅保留：实际返回字段（字段名/类型/示例值/可空性）

### 变更 B：新增聚合结论文档

- `--all` 模式运行后生成 `reports/all-sources-aggregate.md`
- 聚合文档包含 4 部分：
  - **Part 1**: 数据源采集状态汇总表
  - **Part 2**: 各数据源实际字段清单汇编
  - **Part 3**: 11 张报表字段映射模板（字段 x 数据源列）
  - **Part 4**: AI 分析提示语
- `--source xxx` 仍只生成单独 raw.md，不触发聚合文档

### 变更 C：废弃 validation.md 双文件策略

- 移除 `init_validation_report()` 函数及所有调用点
- 移除 `sources/awin.py`、`sources/social_media.py`、`sources/youtube_studio.py` 中的导入和调用
- 人工标注工作流由 AI 分析替代

### 变更 D：AI 分析提示语

- 聚合文档 Part 4 内嵌完整的 AI 分析指导提示语
- 指导 AI 使用真实字段完成 4 态映射（可映射/需转换/缺失/待人工确认）
- 采集失败的数据源在分析中标注为"数据暂缺"

---

## 3. 影响分析

### 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `reporter.py` | 重构 | 移除旧函数，新增 `write_aggregate_report()` 及 4 个渲染子函数 |
| `validate.py` | 修改 | `_run_source()` 返回 Dict（含 fields），--all 调用聚合生成 |
| `config/field_requirements.yaml` | 重写 | 新结构：reports 列表，11 张报表完整定义 |
| `sources/awin.py` | 修改 | 移除 `init_validation_report` 导入和调用 |
| `sources/social_media.py` | 修改 | 移除 `init_validation_report` 导入和调用 |
| `sources/youtube_studio.py` | 修改 | 移除 `init_validation_report` 导入和调用 |
| `tests/test_reporter.py` | 重写 | 适配新函数签名和行为 |
| `tests/test_validate.py` | 重写 | 新 mock 策略（patch importlib.import_module） |
| `tests/test_structure.py` | 修改 | 断言 `write_aggregate_report` 替代 `init_validation_report` |
| `tests/test_field_requirements.py` | 重写 | 适配新 YAML 结构 |
| `tests/test_e2e.py` | 重写 | 新 mock 策略 + 聚合文档断言 |
| `architecture.md` | 更新 | 报告策略、数据流、目录结构等多处同步 |

### 测试验证

- 103 个测试全部通过（`test_reporter` + `test_validate` + `test_structure` + `test_field_requirements` + `test_e2e`）
- 不影响其他 source 模块的预存测试

---

## 4. 实施状态

**状态：** 已完成

**实施日期：** 2026-04-09
