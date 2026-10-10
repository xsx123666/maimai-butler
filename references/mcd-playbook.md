# 麦当劳 MCP 工具手册（实测版）

> 实测时间：2026-10-09（实测账号：无收藏门店、无历史订单、积分为 0）
> ⚠️ 标记为实测踩坑点，**动手前必读本章**。
> 全量工具共 **35 个**，本手册覆盖三大模块所需的全部核心链路。

---

## 一、配对规则（最重要，先背这张表）

| 场景 | beType | orderType | beCode | 备注 |
|---|---|---|---|---|
| 到店自取 | 1 | 1 | **不传** | 默认场景，最常用 |
| 得来速(DT) | 5 | 1 | 必传（来自 query-nearby-stores） | |
| 麦乐送(外送) | 2 | 2 | 必传（来自 delivery-query-stores） | create-order 需 addressId |
| 企业团餐 | 6 | 2 | 必传（来自 delivery-query-stores） | 需 gmServiceCode |

⚠️ 到店自取时传 beCode 会报错（beCode 是无效参数，不要传）。

## 二、工具全景（35 个）

**账户与积分**：query-my-account（积分账户）｜ query-lottery-info / draw-lottery / query-my-prizes（积分抽奖）
**订单**：order-list（历史订单）｜ query-order（订单详情）｜ cancel-order（取消订单）
**门店**：query-nearby-stores（到店/得来速）｜ delivery-query-stores / delivery-query-addresses / delivery-create-address（外送门店与地址）
**菜单**：query-meals（菜单列表）｜ query-meal-detail（餐品详情/特调）
**营养**：list-nutrition-foods（全量营养表）
**优惠券**：query-my-coupons（我的券包）｜ query-store-coupons（门店可用券）｜ available-coupons（可领券）｜ auto-bind-coupons（一键领券）｜ query-survey-coupon（问卷券）
**价格与下单**：calculate-price（算价）｜ create-order（下单）
**团餐**：query-meal-assistance / query-promotions
**系统**：now-time-info（当前时间）
**商城**：mall-points-products / mall-product-detail / mall-create-order / mall-order-list / mall-order-detail
**派对**：query-party-city / query-party-store / query-party-store-date / query-party-store-session / party-order-create
**其他**：campaign-calendar（活动日历）

---

## 三、核心工具详解（含实测样例）

### 1. order-list —— 历史订单

- 参数：无
- 返回：`data.list[]`，每条含：
  - `orderId` 订单号｜`orderType`｜`createTime` 下单时间｜`beType`｜`beCode`｜`storeCode`｜`storeName` 门店名｜`orderStatus` 订单状态
  - `orderProductList[]`：`productCode`｜`productName` 商品名｜`quantity`｜`comboItemList[]` 子项列表
  - `realTotalAmount` 总金额（字符串，按元处理）
- ⚠️ **实测：无订单时返回 `{"data":{}}`**（空对象、没有 list 字段）→ 必须先判空再取 `list`
- ⚠️ 套餐类商品可能带 `comboItemList`，营养匹配时需展开子项（实测未覆盖，执行时先打印结构确认）

### 2. list-nutrition-foods —— 营养表（模块一核心）

- 参数：无
- 返回：**伪表格文本**（不是 JSON！），形如：
  ```
  [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
    猪柳麦满分,null,1288,308,16,16,24,781,213
    中薯条,null,1210,289,4,12,38,165,18
  ```
- 字段：`productName` 餐品名｜`energyKj` 千焦｜**`energyKcal` 大卡**｜`protein` 蛋白质(g)｜`fat` 脂肪(g)｜`carbohydrate` 碳水(g)｜`sodium` 钠(mg)｜`calcium` 钙(mg)
- ⚠️ 约 160 条，含规格品（"中薯条/大薯条/小薯条"、"可乐中杯/大杯/小杯"）
- 兜底快照：`assets/demo/nutrition_snapshot.txt`（实测数据副本，工具异常时可兜底）

### 3. query-my-account —— 积分账户

- 参数：无
- 返回：`availablePoint` 可用积分｜`accumulativePoint` 累计｜`currentMouthExpirePoint` 本月将过期｜`nextMouthExpirePoint` 下月将过期｜`usedPoint`｜`expiredPoint`｜`frozenPoint`｜`currency`（"麦享会积分"）
- ⚠️ 字段拼写是 **Mouth**（官方 API 原样），别写成 Month

### 4. query-nearby-stores —— 到店/得来速门店

- 参数：`beType`(1|5 必填)、`searchType`(1=收藏/2=位置搜索，必填)、`city`+`keyword`（searchType=2 时必填）
- 返回：`data[]`：`storeCode`｜`storeName`｜`address`｜`distance`(米)｜`businessStatus`(营业中)｜`businessStartTime/EndTime`｜`reservation`｜`reservationTimeOptions[]{date, today, reservationOptionText}`
- ⚠️ **实测：searchType=1 报 600050「收藏餐厅列表为空」** → 一律用 searchType=2 + 城市/关键词
- ⚠️ 报 600047 = 该位置无门店 → 换关键词再试
- ⚠️ beType=1 返回中无 beCode（正常）；beType=5 返回 beCode 且后续所有工具必传
- ⚠️ `reservation=true` 时 `reservationTimeOptions` 必须**完整展示**（缺任何一条会导致用户无法预约）
- ⚠️ 展示门店时 **storeCode 必须完整展示**

**实测样例**（city=昆明市, keyword=南屏街）：
```json
{"storeCode":"3570220","storeName":"麦当劳昆明柏联广场餐厅","address":"三市街6号柏联广场商场商业廊一层F1号","distance":542,"businessStatus":true,"businessStartTime":"07:00","businessEndTime":"23:00","reservation":true}
```

### 5. query-meals —— 菜单列表（模块二/三核心）

- 参数：`storeCode`、`orderType`、`beType`（全部必填）
- 返回：
  - `data.categories[]`：分类列表（含**「500大卡套餐」**分类，减脂可直接用）
  - `data.meals{code: {...}}`：**以 code 为 key** 的映射表：`name`｜`image`（商品图 URL）｜**`currentPrice`（单位：元，字符串）**｜`originalPrice`｜`discountType`｜`canWithOrder`｜`withOrder`
  - `data.frequent`：常点餐品
- ⚠️ **价格单位是「元」**（如 "33.5"），与 calculate-price 的「分」不同！
- ⚠️ 同一商品在多个分类重复出现，取 code 去重
- 实测商品编码范围：短码（"1100" 巨无霸）与长码（"9900005456" 麦辣鸡腿汉堡三件套）
- 商品图可直接用于卡片：`https://menu-img.mcd.cn/...`（加载失败要 fallback）

### 6. calculate-price —— 算价

- 参数：`storeCode`、`orderType`、`beType`、`items[]{productCode, quantity, couponId?, couponCode?}`
- 返回（⚠️ **所有金额单位：分**）：
  - `productPrice/productOriginalPrice`（商品价）｜`originalPrice` 原价｜`discount` 优惠额｜`price` 现价
  - `productList[]{productCode, productName, quantity, originalSubtotal, subtotal}`
  - `takeWayList[]{code, title, subtitle}`：**取餐方式**（实测值：`eat-in` 堂食 / `take-in-store` 外带）→ 下单时作 `takeWayCode`
  - `enjoyed/enjoyable`：已享受/可享受的优惠
- ⚠️ **实测名称差异**：菜单里"薯条"(code 4810) 在算价返回中显示为"**中薯条**"——匹配时以算价返回名为准更稳
- 实测样例（巨无霸+中薯条+可乐）：
  ```json
  {"originalPrice":5000,"discount":0,"price":5000,
   "productList":[{"productCode":"1100","productName":"巨无霸","originalSubtotal":2650,"subtotal":2650},
                  {"productCode":"4810","productName":"中薯条","originalSubtotal":1400,"subtotal":1400},
                  {"productCode":"9900008751","productName":"可乐","originalSubtotal":950,"subtotal":950}],
   "takeWayList":[{"code":"eat-in","title":"堂食"},{"code":"take-in-store","title":"外带"}]}
  ```

### 7. query-store-coupons —— 门店可用券

- 参数：`storeCode`、`orderType`、`beType`
- 返回：`data[]`：`title` 券名｜`couponId`｜`couponCode` 券码｜`tradeDateTime` 有效期｜`products[]{productCode, productName}` 适用商品｜`promotionId`
- ⚠️ **同一 couponId 可对应多个 couponCode**，展示时按 couponId 分组
- ⚠️ 券的 `products[].productCode` 可能是规格级编码（如 `9900000119`=美式中杯），与菜单 code 体系不一定一致；核券时把 couponId 传给 calculate-price 即可
- 实测样例（昆明柏联广场店）：
  ```json
  {"title":"新人专享-中杯美式7折","couponId":"365A627...","couponCode":"MCD67UA...","tradeDateTime":"2026-10-09 00:00:00-2026-11-07 23:59:59","products":[{"productCode":"9900000119","productName":"美式中杯"}]}
  ```

### 8. auto-bind-coupons —— 一键领券

- 参数：无。自动领取麦麦省所有当前可领券。先领券再查券（query-store-coupons）。

### 9. create-order —— 创建订单（唯一动钱操作 ⚠️）

- 参数：`storeCode`、`orderType`、`beType`、`items[]`（与 calculate-price 一致，含券）、`takeWayCode`（orderType=1 必传，来自 takeWayList）、`addressId`（orderType=2 必传）、`remark`（外送可选，≤50字）、`reservationDate`、`gmServiceCode`（团餐）
- ⚠️ **调用前必须用户确认**（门店+商品+总价）
- 返回后引导："可通过支付链接扫码或打开麦当劳 APP 完成支付，支付完成后回复'支付完成'或'支付失败'"

### 10. query-order —— 订单详情

- 参数：`orderId`。用于支付后查状态/配送进度。

### 11. now-time-info —— 当前时间（无参）

- 返回：`date`(yyyy-MM-dd)｜`datetime`｜`year/month/day`｜`dayOfWeek`｜`timezone`（实测 GMT+08:00）
- 用途：模块一确定"本月/上月"的月份基准。

### 12. query-meal-detail —— 餐品详情/特调

- 参数：`storeCode`、`orderType`、`beType`、`code`
- 用途：查看套餐组成、更换特调商品（含 selectedKey/unselectedKey 规则）
- 展示规则：可特调商品标【可特调】；不主动展开特调列表

### 13. query-my-coupons —— 我的券包

- 参数：`page`（默认1，最多5页）、`pageSize`（默认200，最大200）
- ⚠️ 仅返回券资产，**不校验门店/渠道可用性**；"当前门店可用券"用 query-store-coupons

### 14. cancel-order —— 取消订单

- 参数：`orderId`、`cancelReasonCode`（1=改主意 2=重复下单 3=点错 4=地址错 5=时间错 -1=其它）

---

## 四、订单 ↔ 营养匹配策略（模块一核心逻辑）

营养表是"单品+规格品"体系，订单/算价返回名可能有差异，按以下顺序匹配：

1. **精确匹配**：订单 `productName` == 营养表 `productName`
2. **归一化匹配**：统一全/半角括号与空格（实测差异："纯牛奶（盒装）" vs "纯牛奶(盒装)"）、去 `™` 等符号
3. **规格后缀规则**：
   - 订单名带规格（"中薯条"）→ 直接匹配带规格条目
   - 订单名不带规格（"可乐"）→ 营养表按 中杯/大杯/小杯 拆分 → 默认取"中杯"，并在卡片脚注说明
4. **模糊包含**：互为子串时（"麦旋风" ↔ "奥利奥麦旋风"）取公共部分最长者
5. **多候选无法判断** → 标记 `needsReview`，让 AI 人工裁决（不要乱选）
6. **仍匹配不上** → 标"营养数据暂缺"，单独列出，**不计入**热量合计

⚠️ 套餐类订单商品（如"麦辣鸡腿汉堡三件套"）：营养表若无套餐条目，优先展开 `comboItemList` 子项匹配再加总。

---

## 五、常见错误码

| code | 含义 | 处理 |
|---|---|---|
| 600050 | 收藏餐厅列表为空 | 改用 searchType=2 + 城市关键词 |
| 600047 | 位置附近没有餐厅 | 换关键词/换位置再查 |

---

## 六、执行提醒（写卡片前过一遍）

- [ ] 金额：菜单价「元」；算价结果「分」→ ÷100
- [ ] 门店：先选门店（storeCode）再查菜单；无收藏必走搜索
- [ ] 券：先领（auto-bind-coupons）再查（query-store-coupons）；按 couponId 分组
- [ ] 下单：复述→确认→create-order（带 takeWayCode）
- [ ] 数据溯源：卡片里每个数字都能对应到工具返回，禁止脑补
