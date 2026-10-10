#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦智能管家 · 卡片渲染器
================================================
把数据 JSON 注入卡片模板，输出独立 HTML 文件（可直接打开 / 截图分享）。

用法：
  python render_card.py --type monthly   --data report_data.json --out-dir .
  python render_card.py --type recommend --data recommend.json  --out-dir .
  python render_card.py --type split     --data split.json      --out-dir .

依赖：仅 Python 3 标准库。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = {
    "monthly": "card_monthly.html",
    "recommend": "card_recommend.html",
    "split": "card_split.html",
}
PLACEHOLDER = "/*__MAIMAI_DATA__*/null"


def month_key_of(data):
    mk = data.get("monthKey")
    if mk:
        return str(mk)
    label = str(data.get("monthLabel") or "")
    m = re.search(r"(\d{4})\D+(\d{1,2})", label)
    if m:
        return "%s-%02d" % (m.group(1), int(m.group(2)))
    return date.today().strftime("%Y-%m")


def main():
    ap = argparse.ArgumentParser(description="麦麦智能管家 · 卡片渲染器")
    ap.add_argument("--type", required=True, choices=["monthly", "recommend", "split"])
    ap.add_argument("--data", required=True, help="数据 JSON 文件")
    ap.add_argument("--out-dir", default=".", help="输出目录（默认当前目录）")
    ap.add_argument("--out-name", default=None, help="自定义输出文件名（可选）")
    args = ap.parse_args()

    template_path = os.path.join(SKILL_DIR, "assets", TEMPLATES[args.type])
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    if PLACEHOLDER not in html:
        print(json.dumps({"ok": False, "error": "模板缺少注入占位符: " + PLACEHOLDER}, ensure_ascii=False))
        sys.exit(1)

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")  # 防止 </script> 提前闭合
    html = html.replace(PLACEHOLDER, payload)

    # 输出文件名
    if args.out_name:
        fname = args.out_name
    else:
        today = date.today().strftime("%Y-%m-%d")
        if args.type == "monthly":
            fname = "麦麦月报_%s.html" % month_key_of(data)
        elif args.type == "recommend":
            fname = "麦麦健康推荐_%s.html" % today
        else:
            fname = "麦麦拼单账单_%s.html" % today

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, fname)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(json.dumps({
        "ok": True,
        "type": args.type,
        "file": os.path.abspath(out_path),
        "size": os.path.getsize(out_path),
        "note": "用浏览器打开该文件即可查看卡片；提示用户可截图分享。",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
