#!/usr/bin/env python3
"""逐步调试crawl_projects.py的call_api函数"""
import urllib.request
import urllib.parse
import json

BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"
OK_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

def call_api(page, page_size=50):
    params = urllib.parse.urlencode({'page': page, 'pageSize': page_size})
    url = BASE + "fdcxmxxlb.ashx?" + params
    print(f"  URL: {url}")
    req = urllib.request.Request(url, headers=OK_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('data', [])
            print(f"  返回 {len(items)} 条, totalPage={data.get('totalPage')}")
            return data
    except Exception as e:
        print(f"  API错误: {e}")
        return {'data': [], 'totalPage': 0}

print("测试 call_api...")
result = call_api(1, 50)
print(f"结果类型: {type(result)}, keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
