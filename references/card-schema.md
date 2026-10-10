# 卡片数据 JSON 结构定义（card-schema）

> `scripts/render_card.py` 支持三种卡片类型，数据 JSON 结构如下。
> 所有金额单位为**元**（保留 2 位小数）；热量单位大卡（整数）；蛋白质单位克（整数）。
> 通用字段：`type`（monthly|recommend|split）、`isDemo`（bool，true 时卡片显示 DEMO 角标）、`generatedAt`（yyyy-MM-dd）。

---

## 1. monthly —— 月度饮食报告

```json
{
  "type": "monthly",
  "isDemo": false,
  "monthKey": "2026-09",
  "monthLabel": "2026年9月",
  "generatedAt": "2026-10-09",
  "nickname": "麦友",
  "summary": {
    "totalSpend": 268.50,
    "totalKcal": 12580,
    "totalProtein": 486,
    "orderCount": 12,
    "avgPerOrder": 22.38
  },
  "favoriteItems": [
    { "name": "麦辣鸡腿汉堡", "count": 5, "kcal": 485, "protein": 24, "image": "https://menu-img.mcd.cn/..." }
  ],
  "points": { "available": 1280, "currency": "麦享会积分" },
  "funFacts": [ "热量约等于跑步 147 公里 🏃", "最常搭配：麦辣鸡腿汉堡 + 中薯条" ],
  "unmatched": []
}
```

- `favoriteItems`：TOP3（按出现次数降序，最多 3 条），`count` 为下单次数
- `funFacts`：0-3 条趣味洞察短句
- `unmatched`：营养数据暂缺的餐品名列表（可空数组）

## 2. recommend —— 健康餐推荐

```json
{
  "type": "recommend",
  "goal": "muscle",
  "goalLabel": "增肌 💪",
  "store": { "storeCode": "3570220", "storeName": "麦当劳昆明柏联广场餐厅" },
  "generatedAt": "2026-10-09",
  "combos": [
    {
      "tier": "首选",
      "title": "高蛋白组合",
      "items": [
        { "name": "双层吉士汉堡", "kcal": 429, "protein": 27, "price": 23.0 },
        { "name": "纯牛奶（盒装）", "kcal": 129, "protein": 7, "price": 10.5 }
      ],
      "totalKcal": 558,
      "totalProtein": 34,
      "originalPrice": 33.5,
      "finalPrice": 28.5,
      "saving": 5.0,
      "couponLabel": "新人券 -5元",
      "why": "蛋白质 34g，一顿顶两顿"
    }
  ],
  "note": "价格以门店实际结算为准"
}
```

- `goal`：muscle（增肌）| lose（减脂）| control（控热量）
- `combos`：2-3 个；`tier` 为"首选/备选/轻食"等标签；`saving` 为券省金额（无券则 0）
- `couponLabel`：可空字符串

## 3. split —— 省钱拼单账单

```json
{
  "type": "split",
  "store": { "storeCode": "3570220", "storeName": "麦当劳昆明柏联广场餐厅" },
  "generatedAt": "2026-10-09",
  "peopleCount": 2,
  "people": [
    { "name": "我", "items": ["巨无霸 ×1", "中薯条 ×1"], "subtotal": 40.5 },
    { "name": "朋友A", "items": ["麦辣鸡腿汉堡三件套 ×1"], "subtotal": 33.5 }
  ],
  "bill": {
    "originalPrice": 74.0,
    "discount": 6.0,
    "finalPrice": 68.0,
    "perPerson": 34.0
  },
  "coupons": [ { "title": "新人专享-中杯美式7折", "save": "约 5 元" } ],
  "note": "AA 金额已按人数平均"
}
```

- `people[].items`：字符串数组，格式"商品名 ×数量"
- `bill`：原价 / 优惠 / 应付 / 每人 AA
- `coupons`：参与算账的券（可空数组）

---

## 生成方式

- monthly：由 `scripts/report_calc.py` 自动产出（含匹配率报告）
- recommend / split：由 AI 按上述结构手写 JSON（写入 `.maimai_temp/`），再交 `render_card.py` 渲染

## 渲染命令

```bash
python scripts/render_card.py --type monthly   --data report_data.json  --out-dir <输出目录>
python scripts/render_card.py --type recommend --data recommend.json    --out-dir <输出目录>
python scripts/render_card.py --type split     --data split.json        --out-dir <输出目录>
```

输出文件名自动化：`麦麦月报_<月份>.html` / `麦麦健康推荐_<日期>.html` / `麦麦拼单账单_<日期>.html`（可用 `--out-name` 覆盖）。
