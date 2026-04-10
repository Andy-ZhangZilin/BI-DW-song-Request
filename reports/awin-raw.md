# awin 字段验证报告（Raw）

**生成时间：** 2026-04-10 11:49:46

## 接口：N/A

**样本记录数：** 20

| 字段名 | 类型 | 示例值 | 可空 | 来源 |
|--------|------|--------|------|------|
| aov | number | 143.807 | 是 | 计算：totalValue / totalNo |
| clicks | integer | 3 | 否 | API 直接 |
| conversionRate | number | 0.3286 | 是 | 计算：totalNo / clicks |
| cpa | number | 14.3804 | 是 | 计算：totalComm / totalNo |
| cpc | number | 4.725 | 是 | 计算：totalComm / clicks |
| impressions | integer | 35 | 否 | API 直接 |
| roi | number | 10.0002 | 是 | 计算：totalValue / totalComm |
| totalComm | number | 330.75 | 否 | API 直接 |
| totalNo | integer | 23 | 否 | API 直接 |
| totalValue | number | 3307.56 | 否 | API 直接 |
