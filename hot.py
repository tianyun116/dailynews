import requests
import json
import re
from datetime import datetime
import os

# 权重
W = {"weibo": 0.5, "baidu": 0.3, "zhihu": 0.2}

def fetch_weibo():
    # 示例接口，如失效请自行更换
    url = "https://tenapi.cn/v2/weibohot"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = r.json().get("data", [])
    return [{"title": it["name"], "platform": "weibo", "raw_hot": it.get("hot", 0)} for it in data]

def fetch_baidu():
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    cards = r.json().get("data", {}).get("cards", [])
    items = []
    for card in cards:
        for c in card.get("content", []):
            items.append({"title": c["word"], "platform": "baidu", "raw_hot": c.get("hotScore", 0)})
    return items

def fetch_zhihu():
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = r.json().get("data", [])
    items = []
    for d in data:
        t = d.get("target", {})
        title = t.get("title", "")
        detail = t.get("detail_text", "0")
        num = re.findall(r'[\d.]+', detail.replace(",",""))
        raw = float(num[0])*10000 if "万" in detail else float(num[0]) if num else 0
        items.append({"title": title, "platform": "zhihu", "raw_hot": raw})
    return items

def normalize_weight(items, weight):
    if not items: return []
    hots = [x["raw_hot"] for x in items]
    mn, mx = min(hots), max(hots)
    if mx == mn:
        for x in items: x["score"] = 1.0 * weight
    else:
        for x in items: x["score"] = ((x["raw_hot"] - mn) / (mx - mn)) * weight
    return items

def simple_merge(items):
    merged = []
    for item in items:
        found = False
        for m in merged:
            if item["title"] in m["title"] or m["title"] in item["title"]:
                m["total_score"] += item["score"]
                if item["platform"] not in m["sources"]:
                    m["sources"].append(item["platform"])
                found = True
                break
        if not found:
            merged.append({"title": item["title"], "total_score": item["score"], "sources": [item["platform"]]})
    return merged

all_items = []
try: all_items.extend(normalize_weight(fetch_weibo(), W["weibo"]))
except: pass
try: all_items.extend(normalize_weight(fetch_baidu(), W["baidu"]))
except: pass
try: all_items.extend(normalize_weight(fetch_zhihu(), W["zhihu"]))
except: pass

merged = simple_merge(all_items)
merged.sort(key=lambda x: x["total_score"], reverse=True)

with open("hot_ranking.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"更新完成，共 {len(merged)} 条")
