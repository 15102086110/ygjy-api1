#!/usr/bin/env python3
"""测试get_all_projects函数"""
import urllib.request
import urllib.parse
import json
import time
from datetime import datetime

BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"
OK_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

def call_api(page, page_size=50):
    params = urllib.parse.urlencode({'page': page, 'pageSize': page_size})
    url = BASE + "fdcxmxxlb.ashx?" + params
    req = urllib.request.Request(url, headers=OK_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  API错误: {e}")
        return {'data': [], 'totalPage': 0}

def get_all_projects(start_year=2019, end_year=2026):
    all_projects = []
    seen_ids = set()
    page = 1
    max_pages = 5  # 先只测5页
    reached_old = False

    print(f"开始获取 {start_year}-{end_year} 年数据...")
    print(f"测试模式：只获取前 {max_pages} 页\n")

    while page <= max_pages and not reached_old:
        print(f"  正在获取第 {page} 页... (已获取 {len(all_projects)} 条)")

        data = call_api(page, 50)
        items = data.get('data', [])
        print(f"  API返回 {len(items)} 条原始数据")

        if not items:
            print(f"第 {page} 页无数据，停止获取")
            break

        accepted = 0
        for item in items:
            project_id = item.get('projectId')
            if not project_id or project_id in seen_ids:
                continue
            seen_ids.add(project_id)

            presell = str(item.get('presell') or '')
            year = None
            if presell and len(presell) >= 4 and presell[:4].isdigit():
                year = int(presell[:4])

            print(f"    {project_id}: {item.get('projectName')} | presell={presell} | year={year}")

            if year and year < start_year:
                print(f"  ✅ 已到达 {year} 年数据，停止获取")
                reached_old = True
                break

            if year and year >= start_year and year <= end_year:
                all_projects.append({
                    'projectId': project_id,
                    'projectName': item.get('projectName', ''),
                    'year': year,
                    'presell': presell,
                })
                accepted += 1

        print(f"  本页接受 {accepted} 条\n")
        page += 1
        time.sleep(0.3)

    print(f"\n获取完成，共 {len(all_projects)} 个楼盘")
    return all_projects

print("测试 get_all_projects...")
results = get_all_projects(2019, 2026)
print(f"\n最终结果: {len(results)} 条")
for r in results[:3]:
    print(f"  - {r['projectName']} ({r['presell']})")
