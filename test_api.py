#!/usr/bin/env python3
# test_api.py - 测试阳光家缘API
import urllib.request
import json

url = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/fdcxmxxlb.ashx?page=1&pageSize=3"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print(f"返回 {len(data.get('data', []))} 条数据")
    for p in data.get('data', [])[:3]:
        print(f"  - {p.get('projectName')}")
