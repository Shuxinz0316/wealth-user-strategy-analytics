# 数据字典

本项目全部数据均由 `src/generate_data.py` 使用固定随机种子生成，不包含任何真实用户、账户或交易信息。

## users

用户主表，一名用户一行。

| 字段 | 类型 | 含义 |
|---|---|---|
| `user_id` | INTEGER | 匿名用户主键 |
| `registered_at` | DATETIME | 注册时间 |
| `acquisition_channel` | TEXT | 获客渠道：自然、搜索、社交、推荐、银行合作 |
| `age_group` | TEXT | 年龄区间，不使用精确年龄 |
| `city_tier` | TEXT | 城市层级 |
| `risk_profile` | TEXT | 风险偏好：谨慎、平衡、进取 |
| `initial_cash_balance` | REAL | 初始可投资现金余额（模拟） |
| `marketing_consent` | INTEGER | 是否同意营销触达 |

## products

产品维表，覆盖货币基金、债券基金、混合基金、权益基金、保险和银行理财。

| 字段 | 含义 |
|---|---|
| `product_id` | 产品主键 |
| `product_name` | 产品展示名称 |
| `product_type` | 产品类别 |
| `risk_level` | 产品风险等级 1—4 |
| `expected_return` | 模拟预期收益率；不构成投资建议 |
| `minimum_investment` | 起投金额 |

## events

用户行为明细表。`event_type` 包含 `register`、`app_visit`、`account_open`、`content_view` 和 `product_detail`。可用来还原注册、访问、开户和内容消费路径。

## transactions

申购与赎回流水。`transaction_type` 为 `buy` 或 `redeem`，`amount` 始终为正值；净流入需要按交易类型加减。

## experiment_assignments

沉睡用户召回随机实验。包含分组、是否送达、7 日点击、30 日购买、购买金额、30 日留存和实验前特征。主分析采用 ITT（按初始分组分析），避免只分析已送达人群带来的选择偏差。

## campaign_observations

区域灰度召回活动的用户—月份面板。`pilot_group × post_period` 是 DID 处理变量，`active_30d` 是主要结果，`net_inflow` 是业务结果。

