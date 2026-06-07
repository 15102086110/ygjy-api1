#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取2019-2026年广州住宅楼盘数据
使用方法: python3 crawl_projects.py
"""
import urllib.request
import urllib.parse
import json
import time
import os
import pymongo
from datetime import datetime

# 阳光家缘API配置
BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

# 能工作的headers（和test_api.py一致）
OK_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

# MongoDB配置（从环境变量读取，兜底用默认值）
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0'
)


def call_api(page, page_size=50):
    """调用阳光家缘API（pageSize最大50）"""
    params = urllib.parse.urlencode({'page': page, 'pageSize': page_size})
    url = BASE + "fdcxmxxlb.ashx?" + params
    req = urllib.request.Request(url, headers=OK_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"  ❌ API错误(page={page}): {e}")
        return {'data': [], 'totalPage': 0}


def get_all_projects(start_year=2019, end_year=2026):
    """获取指定年份范围内的所有楼盘数据"""
    all_projects = []
    seen_ids = set()
    page = 1
    max_pages = 250  # 250页 × 50条 = 12500条，覆盖全部数据
    reached_old = False

    print(f"开始获取 {start_year}-{end_year} 年数据...")
    print(f"预计总页数: ~237页 (pageSize=50)\n")

    while page <= max_pages and not reached_old:
        print(f"  📄 正在获取第 {page} 页... (已获取 {len(all_projects)} 条)", end="\r")

        data = call_api(page, 50)
        items = data.get('data', [])

        if not items:
            print(f"\n⚠️  第 {page} 页无数据，停止获取")
            break

        for item in items:
            project_id = item.get('projectId')
            if not project_id or project_id in seen_ids:
                continue
            seen_ids.add(project_id)

            # 从presell字段提取年份
            presell = str(item.get('presell') or '')
            year = None
            if presell and len(presell) >= 4 and presell[:4].isdigit():
                year = int(presell[:4])

            # 如果已经到达2019年之前的数据，停止
            if year and year < start_year:
                print(f"\n✅ 已到达 {year} 年数据，停止获取")
                reached_old = True
                break

            if year and year >= start_year and year <= end_year:
                all_projects.append({
                    'projectId': project_id,
                    'projectName': item.get('projectName', ''),
                    'developer': item.get('developer', ''),
                    'presell': presell,
                    'projectAddress': item.get('projectAddress', ''),
                    'houseSoldNum': int(item.get('houseSoldNum', 0) or 0),
                    'houseUnsaleNum': int(item.get('houseUnsaleNum', 0) or 0),
                    'developerId': item.get('developerId', ''),
                    'year': year,
                    'crawlTime': datetime.now().isoformat()
                })

        page += 1
        time.sleep(0.3)  # 避免请求过快

    print(f"\n✅ 获取完成，共 {len(all_projects)} 个楼盘")
    return all_projects


def save_to_mongodb(projects):
    """保存到MongoDB"""
    if not projects:
        print("⚠️  没有数据可保存")
        return False

    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client['ygjy_db']
        collection = db['projects_2019_2026']

        # 清空旧数据
        collection.delete_many({})
        print(f"🗑️  已清空旧数据")

        # 分批插入（每次1000条）
        batch_size = 1000
        for i in range(0, len(projects), batch_size):
            batch = projects[i:i+batch_size]
            collection.insert_many(batch)
            print(f"  💾 已保存 {i+len(batch)}/{len(projects)}", end="\r")
        print()  # 换行

        # 创建索引
        collection.create_index('projectId', unique=True)
        collection.create_index('presell')
        collection.create_index('year')
        collection.create_index([('projectName', 'text'), ('developer', 'text'), ('presell', 'text')])
        print("✅ MongoDB索引创建完成")

        # 打印年份统计
        years = {}
        for p in projects:
            y = p.get('year', 0)
            years[y] = years.get(y, 0) + 1
        print("\n📊 按年份统计:")
        for y in sorted(years.keys()):
            print(f"  {y}年: {years[y]} 个楼盘")

        return True
    except Exception as e:
        print(f"❌ MongoDB错误: {e}")
        return False


def main():
    print("=" * 50)
    print("  广州楼盘数据获取工具 (2019-2026)")
    print("=" * 50)

    # 获取数据
    projects = get_all_projects(2019, 2026)

    if projects:
        # 保存到MongoDB
        save_to_mongodb(projects)

        # 同时保存到本地JSON（备份）
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projects_2019_2026.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存到本地: {filepath}")
    else:
        print("\n❌ 获取数据失败")


if __name__ == '__main__':
    main()
