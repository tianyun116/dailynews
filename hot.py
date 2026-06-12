import requests
import json
import re

W = {"weibo": 0.5, "baidu": 0.3, "zhihu": 0.2}

def fetch_weibo():
    """微博热搜 - 使用官方接口"""
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": "SUB=_2AkMRPq2cf8NxqwJRmP8TyWrlZY10yQvEieKk4uP4JRMyHRl-yD9kqmgNtRB6O4L_vIJPHmviB5THvqsEWb4kRHz4S-Xx"  # 临时cookie，可能过期
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("data", {}).get("realtime", [])
        items = []
        for it in data[:30]:
            items.append({
                "title": it.get("word", ""),
                "platform": "weibo",
                "raw_hot": it.get("raw_hot", 0)
            })
        print(f"微博抓取成功: {len(items)} 条")
        return items
    except Exception as e:
        print(f"微博失败: {e}")
        return []

def fetch_baidu():
    """百度热搜"""
    url = "https://top.baidu.com/board?tab=realtime"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # 百度把数据藏在 <!--s-data:...--> 注释里
        match = re.search(r'<!--s-data:\s*({.*?})\s*-->', r.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            cards = data.get("cards", [])
            items = []
            for card in cards:
                for c in card.get("content", []):
                    items.append({
                        "title": c.get("word", ""),
                        "platform": "baidu",
                        "raw_hot": c.get("hotScore", 0)
                    })
            print(f"百度抓取成功: {len(items)} 条")
            return items
        else:
            print("百度数据解析失败")
            return []
    except Exception as e:
        print(f"百度失败: {e}")
        return []

def fetch_zhihu():
    """知乎热榜"""
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json().get("data", [])
        items = []
        for d in data:
            t = d.get("target", {})
            title = t.get("title", "")
            detail = t.get("detail_text", "0")
            num = re.findall(r'[\d.]+', detail.replace(",",""))
            raw = float(num[0])*10000 if "万" in detail else float(num[0]) if num else 0
            items.append({
                "title": title,
                "platform": "zhihu",
                "raw_hot": raw
            })
        print(f"知乎抓取成功: {len(items)} 条")
        return items
    except Exception as e:
        print(f"知乎失败: {e}")
        return []

def normalize_weight(items, weight):
    if not items:
        return []
    hots = [x["raw_hot"] for x in items]
    mn, mx = min(hots), max(hots)
    if mx == mn:
        for x in items:
            x["score"] = 1.0 * weight
    else:
        for x in items:
            x["score"] = ((x["raw_hot"] - mn) / (mx - mn)) * weight
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
            merged.append({
                "title": item["title"],
                "total_score": item["score"],
                "sources": [item["platform"]]
            })
    return merged

# 开始抓取
all_items = []

weibo_data = fetch_weibo()
if weibo_data:
    all_items.extend(normalize_weight(weibo_data, W["weibo"]))

baidu_data = fetch_baidu()
if baidu_data:
    all_items.extend(normalize_weight(baidu_data, W["baidu"]))

zhihu_data = fetch_zhihu()
if zhihu_data:
    all_items.extend(normalize_weight(zhihu_data, W["zhihu"]))

print(f"\n总计抓取到 {len(all_items)} 条原始数据")

if all_items:
    merged = simple_merge(all_items)
    merged.sort(key=lambda x: x["total_score"], reverse=True)
    print(f"合并完成，共 {len(merged)} 条")
else:
    merged = []
    print("所有平台均失败，榜单为空")

with open("hot_ranking.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f"hot_ranking.json 已保存，共 {len(merged)} 条")
