import requests
import json
import re

# 各平台权重
W = {"weibo": 0.5, "baidu": 0.3, "zhihu": 0.2}

def fetch_weibo():
    # 备用免费接口
    url = "https://tenapi.cn/v2/weibohot"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json().get("data", [])
        if not data:
            print("微博接口返回空数据")
        return [{"title": it["name"], "platform": "weibo", "raw_hot": it.get("hot", 0)} for it in data]
    except Exception as e:
        print(f"微博失败: {e}")
        return []

def fetch_baidu():
    # 备用接口：从页面提取数据
    url = "https://top.baidu.com/board?tab=realtime"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        # 从页面中提取初始数据
        match = re.search(r'<!--s-data:(.*?)-->', r.text, re.DOTALL)
        if not match:
            print("百度页面解析失败")
            return []
        data = json.loads(match.group(1))
        cards = data.get("cards", [])
        items = []
        for card in cards:
            for c in card.get("content", []):
                items.append({"title": c["word"], "platform": "baidu", "raw_hot": c.get("hotScore", 0)})
        return items
    except Exception as e:
        print(f"百度失败: {e}")
        return []

def fetch_zhihu():
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
    try:
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
            merged.append({"title": item["title"], "total_score": item["score"], "sources": [item["platform"]]})
    return merged

all_items = []

# 逐个抓取，哪个成功用哪个
weibo_data = fetch_weibo()
if weibo_data:
    all_items.extend(normalize_weight(weibo_data, W["weibo"]))
    print(f"微博抓取成功: {len(weibo_data)} 条")

baidu_data = fetch_baidu()
if baidu_data:
    all_items.extend(normalize_weight(baidu_data, W["baidu"]))
    print(f"百度抓取成功: {len(baidu_data)} 条")

zhihu_data = fetch_zhihu()
if zhihu_data:
    all_items.extend(normalize_weight(zhihu_data, W["zhihu"]))
    print(f"知乎抓取成功: {len(zhihu_data)} 条")

if not all_items:
    print("所有平台抓取失败，生成空数据")
    # 写入空数组，这样前端显示"暂无数据"
else:
    merged = simple_merge(all_items)
    merged.sort(key=lambda x: x["total_score"], reverse=True)
    print(f"合并完成，共 {len(merged)} 条")

merged = simple_merge(all_items) if all_items else []
if merged:
    merged.sort(key=lambda x: x["total_score"], reverse=True)

with open("hot_ranking.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"文件已保存，共 {len(merged)} 条")
