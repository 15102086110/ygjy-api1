#!/usr/bin/env python3
# 测试阳光家缘API - 不同pageSize
import urllib.request
import urllib.parse
import json

BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/',
}

print("测试不同pageSize:")
for size in [3, 5, 10, 20, 50, 100, 200]:
    params = urllib.parse.urlencode({'page': 1, 'pageSize': size})
    url = BASE + "fdcxmxxlb.ashx?" + params
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            items = data.get('data', [])
            total = data.get('totalPage', 'N/A')
            print(f"  pageSize={size}: 返回 {len(items)} 条, totalPage={total}")
    except Exception as e:
        print(f"  pageSize={size}: 错误 {e}")