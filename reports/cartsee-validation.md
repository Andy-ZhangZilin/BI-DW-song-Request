# CartSee 爬虫验证报告

**验证时间：** 2026-04-07
**分支：** dev
**服务器：** 123.57.152.198
**账号：** zhoudong@hqkj.com

---

## 测试结果

| 测试类型 | 测试项 | 结果 |
|---|---|---|
| 单元测试 | test_extract_fields_returns_field_info_structure | PASSED |
| 单元测试 | test_extract_fields_empty_sample | PASSED |
| 单元测试 | test_extract_fields_correct_types | PASSED |
| 单元测试 | test_extract_fields_nullable_detection | PASSED |
| 单元测试 | test_extract_fields_all_four_keys_present | PASSED |
| 集成测试 | test_authenticate_with_real_credentials | PASSED |
| 集成测试 | test_fetch_sample_returns_records | PASSED |

**总计：7 / 7 全部通过**

---

## 实际抓取数据

**本次抓取记录数：** 20 条（营销活动列表第一页，共 924 条）

### 代表性记录（已发送活动）

```json
{
  "活动名称": "0407 营销\n发送于2026-04-07 22:30:00(GMT+08:00)-近30天打开邮件至少1次近60天订阅用户 - 0207近15天下单用户",
  "活动ID": "505165",
  "类型": "邮件",
  "已发送数": "90938",
  "送达率": "99.51%\n送达90491封",
  "打开率": "5.78%\n5232位收件人",
  "点击率": "0.30%\n275位收件人",
  "CartSee订单数": "1",
  "CartSee销售额": "59.35",
  "转化率": "0.00%",
  "客单价": "59.35",
  "退回率": "0.42%\n384位收件人",
  "投诉率": "0.00%\n0位收件人",
  "退订率": "0.02%\n16位收件人",
  "点击打开率": "5.26%",
  "操作": ""
}
```

> 注：部分字段（如送达率、打开率等）包含多行文本，上行为百分比，下行为具体数量，爬虫原样保留。

---

## 字段信息（extract_fields 输出）

> 示例值取自 20 条记录中第一个非空非零的有效值。

| 字段名 | 数据类型 | 示例值 | 可为空 |
|---|---|---|---|
| 活动名称 | string | 0407 营销 发送于2026-04-07... | false |
| 活动ID | string | 505165 | false |
| 类型 | string | 邮件 | false |
| 已发送数 | string | 90938 | false |
| 送达率 | string | 99.51% 送达90491封 | false |
| 打开率 | string | 5.78% 5232位收件人 | false |
| 点击率 | string | 0.30% 275位收件人 | false |
| CartSee订单数 | string | 1 | false |
| CartSee销售额 | string | 59.35 | false |
| 转化率 | string | 0.00% | false |
| 客单价 | string | 59.35 | false |
| 退回率 | string | 0.42% 384位收件人 | false |
| 投诉率 | string | 0.00% 0位收件人 | false |
| 退订率 | string | 0.02% 16位收件人 | false |
| 点击打开率 | string | 5.26% | false |
| 操作 | string | （空） | false |

