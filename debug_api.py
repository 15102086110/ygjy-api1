#!/usr/bin/env python3
"""调试：为什么crawl脚本返回0条数据"""
import urllib.request
import urllib.parse
import json

BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

# 方法1：最简化（和test_api.py一样）
print("=== 方法1：最简请求 ===")
url1 = BASE + "fdcxmxxlb.ashx?page=1&pageSize=3"
req1 = urllib.request.Request(url1, headers={'User-Agent': 'python'})
try:
    with urllib.request.urlopen(req1, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  返回 {len(d.get('data',[]))} 条, totalPage={d.get('totalPage')}")
except Exception as e:
    print(f"  错误: {e}")

# 方法2：带Referer
print("\n=== 方法2：带Referer ===")
headers2 = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}
req2 = urllib.request.Request(BASE + "fdcxmxxlb.ashx?page=1&pageSize=3", headers=headers2)
try:
    with urllib.request.urlopen(req2, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  返回 {len(d.get('data',[]))} 条, totalPage={d.get('totalPage')}")
except Exception as e:
    print(f"  错误: {e}")

# 方法3：用urllib.parse.urlencode构建URL
print("\n=== 方法3：urlencode构建 ===")
params = urllib.parse.urlencode({'page': 1, 'pageSize': 3})
url3 = BASE + "fdcxmxxlb.ashx?" + params
print(f"  URL: {url3}")
req3 = urllib.request.Request(url3, headers=headers2)
try:
    with urllib.request.urlopen(req3, timeout=15) as r:
        d = json.loads(r.read())
        print(f"  返回 {len(d.get('data',[]))} 条, totalPage={d.get('totalPage')}")
except Exception as e:
    print(f"  错误: {e}")
