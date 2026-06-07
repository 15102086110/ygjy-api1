#!/usr/bin/env python3
# 研究阳光家缘API - 尝试获取更多数据
import urllib.request
import urllib.parse
import json

BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://zfcj.gz.gov.cn/',
}

def test_api(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        return {'error': str(e)}

# 1. 测试不同参数
print("=== 测试API参数 ===")
print()

# 获取第1页50条
data = test_api('fdcxmxxlb.ashx', {'page': 1, 'pageSize': 50})
items = data.get('data', [])
print(f"第1页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 获取第2页50条
data = test_api('fdcxmxxlb.ashx', {'page': 2, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第2页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 获取第10页50条
data = test_api('fdcxmxxlb.ashx', {'page': 10, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第10页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 获取第20页50条
data = test_api('fdcxmxxlb.ashx', {'page': 20, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第20页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 获取第50页50条
data = test_api('fdcxmxxlb.ashx', {'page': 50, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第50页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 获取第100页50条
data = test_api('fdcxmxxlb.ashx', {'page': 100, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第100页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")
    print(f"  最后一条预售证: {items[-1].get('presell')}")

# 测试最大页数
data = test_api('fdcxmxxlb.ashx', {'page': 200, 'pageSize': 50})
items = data.get('data', [])
print(f"\n第200页50条: {len(items)} 条")
if items:
    print(f"  第一条预售证: {items[0].get('presell')}")

# 查看API返回的完整结构
data = test_api('fdcxmxxlb.ashx', {'page': 1, 'pageSize': 1})
print(f"\n=== API返回结构 ===")
print(json.dumps(data, ensure_ascii=False, indent=2)[:500])