# 🔌 MCP 集成说明 · MCP_INTEGRATION

> 本文档说明「麦麦智能管家」与**麦当劳中国 MCP Server** 的集成方式：接入信息、工具调用清单、各模块调用链路与业务价值。

---

## 1. MCP Server 信息

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp`（麦当劳中国 MCP 服务） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | 请求头 `Authorization: Bearer YOUR_MCP_TOKEN` |
| Token 申请 | [open.mcd.cn/mcp](https://open.mcd.cn/mcp)（手机号登录 → 控制台 → 激活） |
| 限流说明 | 每个 Token 每分钟最多 600 次请求（超限返回 429） |
| 环境要求 | 需支持 Streamable HTTP 协议的 MCP Client；MCP Version 2025-06-18 及之前版本 |
| 服务范围 | 面向中国大陆地区使用（不含港澳台） |

### 配置示例（WorkBuddy / 通用 MCP Client）

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

---

## 2. 调用的 MCP Tool 清单（按模块分类）

### 📊 模块一：月度饮食报告

| 工具 | 作用 | 关键返回字段 |
|---|---|---|
| `order-list` | 拉取历史订单（无参） | 订单号 / 下单时间 / 门店 / 商品明细（名称·数量）/ 订单金额 |
| `list-nutrition-foods` | 获取全量营养数据（无参） | 约 160 条餐品：热量(kcal) / 蛋白质 / 脂肪 / 碳水 / 钠 / 钙 |
| `query-my-account` | 查询积分账户（无参） | 可用积分 / 累计积分 / 即将过期积分 |
| `now-time-info` | 获取当前时间（无参） | 用于确定"本月 / 上月"统计口径 |

### 💪 模块二：健康餐推荐

| 工具 | 作用 | 关键返回字段 |
|---|---|---|
| `query-nearby-stores` | 按城市+关键词搜索门店 | storeCode / 门店名 / 距离 / 营业状态 |
| `query-meals` | 查询门店菜单 | 商品 code / 名称 / 价格 / 图片 / 分类 |
| `list-nutrition-foods` | 营养数据匹配 | 热量 / 蛋白质等 |
| `calculate-price` | 组合精确算价 | 商品价 / 优惠额 / 应付价（单位：分）/ 取餐方式 |
| `query-store-coupons` | 查询门店可用优惠券 | 券名 / 券ID / 券码 / 有效期 / 适用商品 |

### 💰 模块三：省钱拼单

| 工具 | 作用 | 关键返回字段 |
|---|---|---|
| `query-meals` | 菜单与商品编码 | 同上 |
| `auto-bind-coupons` | 一键领取全部可领优惠券（无参） | 领取结果 |
| `query-store-coupons` | 查看已领到的可用券 | 同上 |
| `calculate-price` | 总价 + 最优券测算 | 原价 / 优惠 / 应付 / AA 基数 |
| `create-order` | 创建订单（**经用户确认后**） | 订单号 / 支付链接 |
| `query-order` | 支付后查询订单状态 | 订单状态 / 配送进度 |

### 🔧 支撑能力（未直接用于上述链路，作为扩展储备）

- **外送场景**：`delivery-query-addresses` / `delivery-create-address` / `delivery-query-stores`
- **团餐场景**：`query-meal-assistance` / `query-promotions`
- **餐品详情**：`query-meal-detail`（套餐组成与特调选项）
- **券包管理**：`query-my-coupons` / `available-coupons` / `query-survey-coupon`
- **积分商城**：`mall-points-products` / `mall-product-detail` / `mall-create-order` / `mall-order-list` / `mall-order-detail`
- **派对 / 抽奖 / 活动**：`query-party-*` / `draw-lottery` / `query-lottery-info` / `query-my-prizes` / `campaign-calendar`
- **订单管理**：`cancel-order`

> MCP Server 共挂载 **35 个工具**，完整参数手册（含实测样例与坑位）见 `references/mcd-playbook.md`。

---

## 3. 各模块调用流程

### 3.1 模块一：月度饮食报告

```
① order-list ─────────────► 拉取历史订单（按 createTime 过滤目标月份）
② list-nutrition-foods ───► 全量营养表（160 条，伪表格文本格式）
③ report_calc.py ─────────► 订单↔营养匹配 → 聚合计算
                             （总消费 / 总热量 / 总蛋白 / 次数 / TOP3 / 匹配率报告）
④ query-my-account ───────► 积分余额
⑤ render_card.py ─────────► 输出 麦麦月报_YYYY-MM.html（品牌卡片）
```

**关键设计：**
- 匹配策略：精确匹配 → 归一化（全半角/空格）→ 规格默认（中杯）→ 模糊包含；未匹配项标注"营养数据暂缺"，不计入合计
- 趣味换算：总热量 → "跑步 X 公里"；总蛋白 → "X 个鸡蛋"

### 3.2 模块二：健康餐推荐

```
① query-nearby-stores ────► 门店搜索（城市+关键词，选定 storeCode）
② query-meals ────────────► 菜单（商品 code / 价格 / 图片 / 分类）
③ list-nutrition-foods ───► 候选商品营养匹配
④ [组合设计] ──────────────► 按目标（增肌 / 减脂 / 控热量）设计 2-3 个组合
⑤ calculate-price ────────► 组合精确算价（返回单位为「分」，展示 ÷100）
⑥ query-store-coupons ────► 可用券 + 每个组合的省钱测算
⑦ render_card.py ─────────► 输出推荐卡片
```

### 3.3 模块三：省钱拼单

```
① [需求收集] ──────────────► 参与人数 + 每人想吃的东西
② query-nearby-stores ────► 选定门店
③ query-meals ────────────► 菜单与商品编码
④ auto-bind-coupons ──────► 一键领取全部可用券
⑤ query-store-coupons ────► 查看可用券（同一 couponId 多券码按组展示）
⑥ calculate-price ────────► 总价 / 优惠 / 每人 AA 测算
⑦ render_card.py ─────────► 输出拼单账单卡片
⑧ [用户确认] ──────────────► 复述"门店 + 商品 + 总价"，等待明确确认 ⚠️
⑨ create-order ───────────► 创建订单（携 takeWayCode，来自 calculate-price 的 takeWayList）
⑩ query-order ────────────► 支付完成后查询订单状态
```

### 3.4 实测关键约束（集成坑位提示）

| 约束 | 说明 |
|---|---|
| 门店依赖 | `query-meals` / `calculate-price` / `query-store-coupons` / `create-order` 均依赖 `storeCode`，需先选门店 |
| 收藏为空 | `query-nearby-stores` 的 searchType=1（收藏）在无收藏时报 600050，需改用 searchType=2 + 城市关键词 |
| 金额单位 | `query-meals` 价格单位是「元」；`calculate-price` 返回单位是「分」（展示前 ÷100） |
| 取餐方式 | `create-order` 需 `takeWayCode`，取值来自 `calculate-price` 返回的 `takeWayList`（实测值：`eat-in` 堂食 / `take-in-store` 外带） |
| 券码分组 | `query-store-coupons` 同一 `couponId` 可对应多个 `couponCode`，展示时按 couponId 分组 |
| 名称差异 | 菜单「薯条」在算价返回中为「中薯条」；营养匹配以算价返回名为准更稳 |

---

## 4. 业务价值说明

### 4.1 解决的问题

**模块一：把"散落的订单"变成"看得懂的饮食画像"**
- 现状：用户能在麦当劳 APP 看到订单，但看不到"这个月一共花了多少、摄入多少热量、最常吃什么"
- 方案：用 MCP 订单数据 × 官方营养数据做交叉分析，产出可分享的 Wrapped 式报告
- 价值：消费可视化 + 健康意识唤醒 + 社交传播（分享卡片自带品牌视觉）

**模块二：化解"想吃麦麦"与"怕不健康"的矛盾**
- 现状：麦当劳常被贴上"不健康"标签，但官方营养表（160+ 条）其实支持科学搭配
- 方案：把营养数据翻译成"目标导向的方案"——增肌 / 减脂 / 控热量，带精确价格与券后省额
- 价值：降低点餐决策成本，给用户"放心点、敢点"的理由

**模块三：让"多人点餐"省钱又省事**
- 现状：多人拼单算账麻烦、优惠券利用率低、AA 容易算错
- 方案：自动领券 + 自动算账 + AA 拆分 + （确认后）一键下单的完整闭环
- 价值：省钱（券核销率提升）+ 省事（AA 一秒算出）+ 转化（从推荐直达下单）

### 4.2 对麦当劳生态的价值

- **工具使用深度**：将 6 个核心 MCP 工具编排为完整的用户旅程（查询 → 分析 → 推荐 → 下单）
- **券核销促进**：`auto-bind-coupons` → `query-store-coupons` → `calculate-price` 全链路贯穿拼单场景
- **会员触达**：积分体系在月报卡片中自然曝光，增强会员粘性
- **品牌传播**：分享型卡片以麦当劳品牌视觉在社交场景扩散

### 4.3 技术亮点

- **Skill + MCP 编排模式**：把 35 个原始工具封装为"业务级用户价值"（3 个场景、3 张卡片）
- **确定性计算与 AI 编排分离**：价格 / 营养聚合全部由 Python 脚本确定性完成（可复现、可审计），AI 只负责流程编排与呈现
- **视觉即产品**：数据直接产出可分享的品牌卡片，而非文字堆砌
- **兜底容错设计**：无订单 → 演示数据；工具异常 → 营养快照兜底；全程 DEMO 标注与数据溯源
