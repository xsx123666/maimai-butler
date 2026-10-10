#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦智能管家 · 月度报告数据计算器
================================================
把麦当劳订单数据与营养数据匹配聚合，输出可渲染的 report_data.json。

用法：
  python report_calc.py \
    --orders .maimai_temp/orders.json \
    --nutrition .maimai_temp/nutrition.txt \
    --points .maimai_temp/points.json \
    --month 2026-09 \
    --out .maimai_temp/report_data.json

  # 演示数据 / 全量统计（不过滤月份）：
  python report_calc.py --orders demo_orders.json --nutrition nutrition_snapshot.txt \
    --month all --demo --out report_data.json

依赖：仅 Python 3 标准库。
"""
import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------- 基础工具

def load_orders(path):
    """兼容多种订单数据形态，取出订单数组。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = []
    if isinstance(raw, dict):
        data = raw.get("data", raw)
        if isinstance(data, dict):
            items = data.get("list") or []
        elif isinstance(data, list):
            items = data
    elif isinstance(raw, list):
        items = raw
    return items


def norm(s):
    s = str(s or "").strip()
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("™", "").replace("®", "")
    s = s.replace("　", "")
    s = re.sub(r"\s+", "", s)
    return s


def month_of(s):
    """从时间字符串提取 YYYY-MM。"""
    m = re.search(r"(\d{4})[-/\.](\d{1,2})", str(s or ""))
    if not m:
        return None
    return "%s-%02d" % (m.group(1), int(m.group(2)))


# ---------------------------------------------------------------- 营养表

def parse_nutrition(path):
    """解析 list-nutrition-foods 的伪表格文本 → {name: {...}}"""
    table = OrderedDict()
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") or line.endswith(":"):
            continue  # 表头行
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 9:
            continue
        name = parts[0]
        try:
            entry = {
                "name": name,
                "kj": float(parts[2]),
                "kcal": int(float(parts[3])),
                "protein": float(parts[4]),
                "fat": float(parts[5]),
                "carbs": float(parts[6]),
                "sodium": float(parts[7]),
                "calcium": float(parts[8]),
            }
        except (ValueError, IndexError):
            continue
        if name not in table:
            table[name] = entry
    return table


def build_index(table):
    idx = {}
    for name in table:
        k = norm(name)
        if k not in idx:
            idx[k] = name
    return idx


def match_item(order_name, table, nidx):
    """订单商品名 → 营养表条目。返回 (表内名称 or None, 匹配方式)。"""
    n = norm(order_name)
    if not n:
        return None, "unmatched"
    # 1) 精确
    if order_name in table:
        return order_name, "exact"
    # 2) 归一化精确
    if n in nidx:
        return nidx[n], "normalized"
    # 3) 互为子串（模糊）
    cands = []
    for kn, orig in nidx.items():
        if n in kn or kn in n:
            cands.append((abs(len(kn) - len(n)), orig))
    if cands:
        cands.sort(key=lambda x: x[0])
        # 规格默认：候选含“中杯”优先
        for _, orig in cands:
            if "中杯" in norm(orig):
                return orig, "spec-default"
        return cands[0][1], "fuzzy"
    return None, "unmatched"


# ---------------------------------------------------------------- 趣味洞察

def build_facts(kcal, protein, spend, count):
    facts = []
    if kcal > 0:
        facts.append("这些热量要跑步约 %d 公里才能消耗掉 🏃" % round(kcal / 70))
        facts.append("热量总和约等于 %.1f 个巨无霸 🍔" % (kcal / 513.0))
    if protein > 0:
        facts.append("蛋白质总量约等于 %d 个鸡蛋 🥚" % round(protein / 6.0))
    if count > 0:
        facts.append("平均每 %d 天就要光顾一次麦麦 📅" % max(1, 30 // count))
    return facts[:3]


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="麦麦智能管家 · 月度报告计算器")
    ap.add_argument("--orders", required=True, help="订单 JSON 文件")
    ap.add_argument("--nutrition", required=True, help="营养表文本文件")
    ap.add_argument("--points", default=None, help="积分 JSON 文件（可选）")
    ap.add_argument("--month", required=True, help="YYYY-MM 或 all")
    ap.add_argument("--demo", action="store_true", help="标记为演示数据")
    ap.add_argument("--nickname", default="麦友", help="用户称呼")
    ap.add_argument("--out", required=True, help="输出 report_data.json 路径")
    args = ap.parse_args()

    orders = load_orders(args.orders)
    table = parse_nutrition(args.nutrition)
    nidx = build_index(table)

    # 月份过滤
    if args.month != "all":
        orders = [o for o in orders if month_of(o.get("createTime")) == args.month]

    # 聚合
    total_spend = 0.0
    total_kcal = 0
    total_protein = 0.0
    counter = {}          # 商品名 -> {count, kcal, protein}
    unmatched = []        # 匹配不上
    needs_review = []     # 模糊匹配、建议人工复核
    match_stats = {"exact": 0, "normalized": 0, "spec-default": 0, "fuzzy": 0}

    for o in orders:
        try:
            total_spend += float(o.get("realTotalAmount") or 0)
        except (TypeError, ValueError):
            pass
        for p in (o.get("orderProductList") or []):
            pname = str(p.get("productName") or "").strip()
            try:
                qty = int(p.get("quantity") or 1)
            except (TypeError, ValueError):
                qty = 1
            tname, how = match_item(pname, table, nidx)
            if tname is None:
                if pname:
                    unmatched.append(pname)
                continue
            e = table[tname]
            total_kcal += e["kcal"] * qty
            total_protein += e["protein"] * qty
            if how in match_stats:
                match_stats[how] += 1
            if how in ("fuzzy", "spec-default") and norm(pname) != norm(tname):
                needs_review.append("%s → %s" % (pname, tname))
            c = counter.setdefault(tname, {"count": 0, "kcal": e["kcal"], "protein": e["protein"]})
            c["count"] += qty

    # 积分
    points = 0
    if args.points and os.path.exists(args.points):
        try:
            with open(args.points, "r", encoding="utf-8") as f:
                praw = json.load(f)
            pdata = praw.get("data", praw) if isinstance(praw, dict) else {}
            points = int(float(pdata.get("availablePoint") or 0))
        except Exception:
            points = 0

    # 月份标签
    if args.month == "all":
        months = [month_of(o.get("createTime")) for o in orders]
        months = [m for m in months if m]
        mk = max(months) if months else date.today().strftime("%Y-%m")
    else:
        mk = args.month
    y, m = mk.split("-")
    month_label = "%d年%d月" % (int(y), int(m))

    # TOP3
    tops = sorted(counter.items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:3]
    favorite = [
        {"name": k, "count": v["count"], "kcal": int(v["kcal"]), "protein": int(v["protein"])}
        for k, v in tops
    ]

    order_count = len(orders)
    data = {
        "type": "monthly",
        "isDemo": bool(args.demo),
        "monthKey": mk,
        "monthLabel": month_label,
        "generatedAt": date.today().strftime("%Y-%m-%d"),
        "nickname": args.nickname,
        "summary": {
            "totalSpend": round(total_spend, 2),
            "totalKcal": int(total_kcal),
            "totalProtein": int(round(total_protein)),
            "orderCount": order_count,
            "avgPerOrder": round(total_spend / order_count, 2) if order_count else 0,
        },
        "favoriteItems": favorite,
        "points": {"available": points, "currency": "麦享会积分"},
        "funFacts": build_facts(total_kcal, total_protein, total_spend, order_count),
        "unmatched": sorted(set(unmatched)),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 输出报告（给 AI 阅读）
    report = {
        "ok": True,
        "out": args.out,
        "month": mk,
        "orders": order_count,
        "summary": data["summary"],
        "top3": favorite,
        "matchReport": {
            "stats": match_stats,
            "unmatched": data["unmatched"],
            "needsReview": needs_review,
        },
        "note": "若 unmatched / needsReview 非空，请人工复核后修正 report_data.json（匹配不上的餐品不计入热量合计）。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
