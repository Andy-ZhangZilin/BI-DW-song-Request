# multi_order 字段验证报告（Raw）

**生成时间：** 2026-04-10
**数据来源：** 本地数据库表 `dws_finance_bi_report_middle_multi_order`
**示例数据：** 多平台订单汇总表.xlsx（导出样本）

## 表：dws_finance_bi_report_middle_multi_order

**样本记录数：** 17

| 字段名 | 类型 | 示例值 | 可空 |
|--------|------|--------|------|
| etl_time | string | 2025-11-01 | 否 |
| 出库时间 | string | NaN | 是 |
| 订购时间 | string | 2025-10-02 | 否 |
| 发货时间 | string | 2025-10-06 | 否 |
| 付款时间 | string | 2025-10-02 | 否 |
| 收入确认时间 | string | NaN | 是 |
| 统计时间 | string | 2025-10-02 | 否 |
| 妥投日期 | string | NaN | 是 |
| ASIN/商品ID | string | B0DG33Y2T3 | 否 |
| MSKU | string | E-CPT017-V2-WBK135-A | 否 |
| SKU | string | CPT017-V2-WBK135-RR-EU | 否 |
| spu | string | CPT017-RR | 否 |
| 报表项目 | string | 管理费用 | 否 |
| 币种 | string | EUR | 否 |
| 大品牌 | string | ROLANSTAR | 否 |
| 大项目 | string | 大家居 | 否 |
| 店铺no | integer | 25 | 否 |
| 店铺名 | string | Amazon-Greenstell Direct-DE | 否 |
| 二级类目 | string | FURNITURE-桌子 | 否 |
| 发货仓库 | string | 872b2005cec44daca3b8259559a88119 | 否 |
| 发货仓库名称 | string | Amazon-Greenstell Direct-DE德国仓 | 否 |
| 发货国家二字码 | string | DE | 否 |
| 品牌 | string | ROLANSTAR | 否 |
| 平台 领星code | integer | 10001 | 否 |
| 平台单号 | string | 305-3446953-1753900 | 否 |
| 平台名称 | string | Amazon | 否 |
| 渠道名称 | string | Amazon-SC （DE） | 否 |
| 三级类目 | string | FURNITURE-电脑桌 | 否 |
| 商城所在国家名称 | string | 德国 | 否 |
| 事业部名称 | string | 大家居欧亚事业部 | 否 |
| 收货国家二字码 | string | DE | 否 |
| 物流方式名称 | string | NaN | 是 |
| 小项目 | string | 家具 | 否 |
| 一级类目 | string | FURNITURE | 否 |
| 原始项目 (源数据表id+该字段) 区分唯一键 | string | 0667b7657f8d4dbeb08bc3a176d5b36f | 否 |
| CNY汇率 | number | 8.3351 | 否 |
| id | integer | 129817006 | 否 |
| 报表id | integer | 1 | 否 |
| 报表日志子项id | integer | 4694 | 否 |
| 报表项目id | integer | 20 | 否 |
| 订单类型 | integer | 0 | 否 |
| 分组号 | integer | 1973500832335405056 | 否 |
| 分组数量 | integer | 12 | 否 |
| 金额 | number | 7.15 | 否 |
| 金额(CNY) | number | 59.595965 | 否 |
| 类型 | integer | 1 | 否 |
| 商品数量 | integer | 1 | 否 |
| 是否删除 | integer | 0 | 否 |
| 源数据表id | integer | 37492451 | 否 |
| 状态 | integer | 34 | 否 |

---

**字段说明补充：**

- `订单类型`：0=普通订单，1=售后订单，2=样品订单
- `类型`：0=多平台订单，1=多平台订单-利润明细
- `是否删除`：0=未删除，1=已删除
- `CNY汇率`：原币种对人民币汇率，用于换算 `金额(CNY)`
- `发货仓库`：为仓库系统内部唯一标识（哈希值），可与 `发货仓库名称` 关联
