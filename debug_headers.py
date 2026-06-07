#!/usr/bin/env python3
"""对比crawl脚本和实际能工作的headers"""
import urllib.request, json

# 能工作的headers（test_api.py用这个）
OK_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

# crawl脚本里的headers
BUG_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://zfcj.gz.gov.cn/zfcj/fyxx/projectdetail/index.html',
}

url = 'https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/fdcxmxxlb.ashx?page=1&pageSize=3'

print('=== 测试OK_HEADERS（test_api.py用这个）===')
req1 = urllib.request.Request(url, headers=OK_HEADERS)
with urllib.request.urlopen(req1, timeout=15) as r:
    d = json.loads(r.read())
    print(f'  返回 {len(d.get("data",[]))} 条')

print('\n=== 测试BUG_HEADERS（crawl脚本用这个）===')
req2 = urllib.request.Request(url, headers=BUG_HEADERS)
with urllib.request.urlopen(req2, timeout=15) as r:
    d = json.loads(r.read())
    print(f'  返回 {len(d.get("data",[]))} 条')
