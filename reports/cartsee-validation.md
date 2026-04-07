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

**本次抓取记录数：** 20 条（营销活动列表第一页）

### 第一条记录示例

```json
{
  "活动名称": "0407 营销\n计划于2026-04-07 22:30:00发送(GMT+08:00)-近30天打开邮件至少1次近60天订阅用户 - 0207近15天下单用户",
  "活动ID": "505165",
  "类型": "邮件",
  "已发送数": "0",
  "送达率": "-\n送达0封",
  "打开率": "-\n0位收件人",
  "点击率": "-\n0位收件人",
  "CartSee订单数": "0",
  "CartSee销售额": "0",
  "转化率": "-",
  "客单价": "0",
  "退回率": "-\n0位收件人",
  "投诉率": "-\n0位收件人",
  "退订率": "-\n0位收件人",
  "点击打开率": "-",
  "操作": ""
}
```

---

## 字段信息（extract_fields 输出）

| 字段名 | 数据类型 | 示例值 | 可为空 |
|---|---|---|---|
| 活动名称 | string | 0407 营销... | false |
| 活动ID | string | 505165 | false |
| 类型 | string | 邮件 | false |
| 已发送数 | string | 0 | false |
| 送达率 | string | -\n送达0封 | false |
| 打开率 | string | -\n0位收件人 | false |
| 点击率 | string | -\n0位收件人 | false |
| CartSee订单数 | string | 0 | false |
| CartSee销售额 | string | 0 | false |
| 转化率 | string | - | false |
| 客单价 | string | 0 | false |
| 退回率 | string | -\n0位收件人 | false |
| 投诉率 | string | -\n0位收件人 | false |
| 退订率 | string | -\n0位收件人 | false |
| 点击打开率 | string | - | false |
| 操作 | string | （空） | false |

---

## 关键修复说明

| 问题 | 根因 | 修复方案 |
|---|---|---|
| URL 错误 | 代码使用 `cartsee.io`，实际为 `app.cartsee.com` | 改为 `app.cartsee.com/cartsee-new/login` 和 `/campaign/list` |
| 登录表单选择器不匹配 | 使用英文 placeholder，实际为中文 Arco Design 组件 | 改为 `input[placeholder='请输入邮箱']`，按钮 `button:has-text('登录')` |
| 登录后 URL 判断过早 | `networkidle` 在 SPA 重定向完成前就触发 | 改用 `wait_for_url(lambda url: "login" not in url)` |
| 表格数据为空 | Arco Design 使用双 `<table>` 结构，表头和数据分离 | 从 `table[0]` 取表头，从 `table[1]` 取数据行 |
| 数据行内容为空 | 导航后 JS 异步渲染未完成就开始提取 | 改用 `wait_for_function` 等待首行 td 有实际文本 |
