#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广州楼盘网签查询 - 统一生产服务器
合并 api_package/index.py + api_server.py + main.py 的全部功能
新增：每日签约数据接口 (/api/signing/daily)
"""
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import pathlib
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.ensure_ascii = False

# ============== 配置 ==============

# 阳光家缘API基础地址
BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

# 能正常工作的请求头（精简版，不带X-Requested-With和长Referer）
OK_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

# MongoDB - 仅从环境变量读取，不硬编码凭据
MONGO_URI = os.environ.get('MONGO_URI', '')

# ============== MongoDB 延迟连接 ==============

db = None

def get_db():
    """获取数据库连接（延迟初始化，仅在需要时连接）"""
    global db
    if db is not None:
        return db
    if not MONGO_URI:
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client['ygjy_db']
        print("✅ MongoDB连接成功")
    except Exception as e:
        print(f"⚠️  MongoDB连接失败: {e}")
        db = None
    return db

# ============== 静态数据（兜底） ==============

PROJECTS_CACHE = []

def load_static_projects():
    """启动时从JSON加载楼盘数据作为兜底"""
    global PROJECTS_CACHE
    json_path = pathlib.Path(__file__).parent / 'projects_2019_2026.json'
    if json_path.exists():
        try:
            with open(json_path, encoding='utf-8') as f:
                PROJECTS_CACHE = json.load(f)
            print(f"✅ 已从JSON加载 {len(PROJECTS_CACHE)} 个楼盘")
            return
        except Exception as e:
            print(f"⚠️  加载JSON失败: {e}")
    print("⚠️  无静态楼盘数据，将完全依赖API")

load_static_projects()

# ============== API调用 ==============

def call_api(path, params=None, max_retry=3):
    """调用阳光家缘API（带指数退避重试）"""
    url = BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=OK_HEADERS)

    for attempt in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                # 如果返回空数据，可能被反爬，也重试
                if isinstance(data, dict) and data.get('total', -1) == 0 and attempt < max_retry - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return data
        except urllib.error.HTTPError as e:
            # HTTP 553 = 反爬限制，指数退避
            if e.code == 553 and attempt < max_retry - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⚠️ HTTP 553, 等待{wait}s后重试...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                raise

# ============== 缓存辅助 ==============

def cache_get(key):
    """从MongoDB获取缓存"""
    database = get_db()
    if database is None:
        return None
    try:
        cached = database.cache.find_one({"_id": key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return cached['data']
    except Exception:
        pass
    return None

def cache_set(key, data, ttl_minutes=5):
    """写入MongoDB缓存"""
    database = get_db()
    if database is None:
        return
    try:
        database.cache.replace_one(
            {"_id": key},
            {"_id": key, "data": data, "expireAt": datetime.now() + timedelta(minutes=ttl_minutes)},
            upsert=True
        )
    except Exception:
        pass

# ============== 工具函数 ==============

def parse_district(address):
    """从地址提取行政区"""
    districts = ['天河区', '海珠区', '荔湾区', '越秀区', '白云区', '黄埔区',
                 '番禺区', '南沙区', '花都区', '增城区', '从化区']
    for d in districts:
        if d in address:
            return d
    return '未知'

# ============== API路由 ==============

@app.route('/')
def index():
    """API首页"""
    return jsonify({
        'name': '广州楼盘网签查询API',
        'version': '4.0.0',
        'dataSource': f'静态数据 {len(PROJECTS_CACHE)} 条 + 实时API',
        'endpoints': [
            '/api/health',
            '/api/projects',
            '/api/projects/<id>',
            '/api/projects/<id>/buildings',
            '/api/buildings/<id>/units',
            '/api/search',
            '/api/stats',
            '/api/signing/daily',
        ]
    })


@app.route('/api/health')
def health():
    """健康检查"""
    db_status = 'disconnected'
    database = get_db()
    if database is not None:
        try:
            database.command('ping')
            db_status = 'connected'
        except Exception:
            db_status = 'error'

    return jsonify({
        'status': 'ok',
        'mongodb': db_status,
        'staticProjects': len(PROJECTS_CACHE),
        'time': datetime.now().isoformat()
    })


@app.route('/api/projects')
def get_projects():
    """获取楼盘列表（优先API，失败用静态数据）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('pageSize', 20)), 50)
    district = request.args.get('district', '')
    keyword = request.args.get('keyword', '') or request.args.get('q', '')
    year = request.args.get('year', '')

    cache_key = f"projects_{page}_{page_size}_{district}_{keyword}_{year}"

    # 1. 查缓存
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # 2. 尝试实时API
    try:
        params = {'page': page, 'pageSize': page_size}
        data = call_api('fdcxmxxlb.ashx', params)
        projects = data.get('data', [])
        total = data.get('total', 0)

        if district:
            projects = [p for p in projects if district in p.get('projectAddress', '')]
        if keyword:
            kw = keyword.lower()
            projects = [p for p in projects
                        if kw in p.get('projectName', '').lower()
                        or kw in p.get('presell', '').lower()
                        or kw in p.get('developer', '').lower()]
        if year:
            projects = [p for p in projects if p.get('presell', '').startswith(str(year))]

        result = {
            'code': 1,
            'data': projects,
            'total': total,
            'page': page,
            'pageSize': page_size,
            'source': 'ygjy'
        }

        cache_set(cache_key, result, ttl_minutes=5)
        return jsonify(result)

    except Exception as e:
        print(f"⚠️  API失败，使用静态数据: {e}")

    # 3. 兜底：静态数据
    result = PROJECTS_CACHE
    if year:
        result = [p for p in result if str(p.get('year')) == str(year)]
    if keyword:
        kw = keyword.lower()
        result = [p for p in result
                  if kw in (p.get('projectName') or '').lower()
                  or kw in (p.get('presell') or '').lower()
                  or kw in (p.get('developer') or '').lower()]
    if district:
        result = [p for p in result if district in (p.get('projectAddress') or '')]

    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size

    result_data = {
        'code': 1,
        'data': result[start:end],
        'total': total,
        'page': page,
        'pageSize': page_size,
        'source': 'static'
    }
    return jsonify(result_data)


@app.route('/api/projects/<project_id>')
def get_project_detail(project_id):
    """楼盘详情"""
    # 先查静态数据
    for p in PROJECTS_CACHE:
        if p.get('projectId') == project_id:
            return jsonify({'code': 1, 'data': p, 'source': 'static'})

    # 查MongoDB
    database = get_db()
    if database is not None:
        try:
            doc = database.projects_2019_2026.find_one({'projectId': project_id}, {'_id': 0})
            if doc:
                return jsonify({'code': 1, 'data': doc, 'source': 'mongodb'})
        except Exception:
            pass

    return jsonify({'code': 0, 'error': 'Not found'}), 404


@app.route('/api/projects/<project_id>/buildings')
def get_buildings(project_id):
    """获取楼栋列表"""
    presell = request.args.get('presell', '')
    cache_key = f"buildings_{project_id}_{presell}"

    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        params = {'sProjectId': project_id}
        if presell:
            params['sPreSellNo'] = presell
        data = call_api('xmldxx.ashx', params)
        buildings = data.get('data', [])

        result = {'code': 1, 'data': buildings, 'source': 'ygjy'}
        cache_set(cache_key, result, ttl_minutes=10)
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)}), 500


@app.route('/api/buildings/<building_id>/units')
def get_units(building_id):
    """获取单元销控数据"""
    house_function = request.args.get('houseFunctionId', '0')
    house_status = request.args.get('houseStatusId', '0')
    cache_key = f"units_{building_id}_{house_function}_{house_status}"

    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        data = call_api('xmxkbxx.ashx', {
            'buildingId': building_id,
            'houseFunctionId': house_function,
            'houseStatusId': house_status
        })

        # 统计各状态数量并保留原始分组结构
        stats = {'unsold': 0, 'signed': 0, 'locked': 0, 'total': 0}
        groups = data.get('data', [])

        for group in groups:
            for unit in group.get('groupData', []):
                status = unit.get('status', 1)
                if status == 1:
                    stats['unsold'] += 1
                elif status == 2:
                    stats['signed'] += 1
                elif status == 3:
                    stats['locked'] += 1
                stats['total'] += 1

        result = {
            'code': 1,
            'data': groups,
            'stats': stats,
            'buildingId': building_id,
            'source': 'ygjy'
        }

        cache_set(cache_key, result, ttl_minutes=5)
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)}), 500


@app.route('/api/search')
def search():
    """搜索楼盘"""
    keyword = request.args.get('q', '') or request.args.get('keyword', '')
    if not keyword:
        return jsonify({'code': 0, 'error': '缺少关键词参数 q 或 keyword'})

    # 先搜静态数据
    kw = keyword.lower()
    static_results = [
        p for p in PROJECTS_CACHE
        if kw in (p.get('projectName') or '').lower()
        or kw in (p.get('presell') or '').lower()
        or kw in (p.get('developer') or '').lower()
    ]

    try:
        # 再搜API数据
        all_api_projects = []
        page = 1
        while len(all_api_projects) < 200:
            data = call_api('fdcxmxxlb.ashx', {'page': page, 'pageSize': 50})
            projects = data.get('data', [])
            if not projects:
                break
            all_api_projects.extend(projects)
            page += 1
            time.sleep(0.3)

        api_results = [
            p for p in all_api_projects
            if kw in p.get('projectName', '').lower()
            or kw in p.get('presell', '').lower()
            or kw in p.get('developer', '').lower()
        ]

        # 合并去重
        seen_ids = set()
        combined = []
        for p in static_results + api_results:
            pid = p.get('projectId', '')
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                combined.append(p)

        return jsonify({
            'code': 1,
            'keyword': keyword,
            'count': len(combined),
            'data': combined[:50]
        })
    except Exception as e:
        # API失败时返回静态结果
        if static_results:
            return jsonify({
                'code': 1,
                'keyword': keyword,
                'count': len(static_results),
                'data': static_results[:50],
                'source': 'static_fallback'
            })
        return jsonify({'code': 0, 'error': str(e)}), 500


@app.route('/api/stats')
def stats():
    """获取统计信息（各区楼盘数量）"""
    cache_key = "stats_districts"

    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        all_projects = []
        page = 1
        while page <= 20:
            data = call_api('fdcxmxxlb.ashx', {'page': page, 'pageSize': 50})
            projects = data.get('data', [])
            if not projects:
                break
            all_projects.extend(projects)
            page += 1
            time.sleep(0.3)

        districts = {}
        for p in all_projects:
            d = parse_district(p.get('projectAddress', ''))
            if d not in districts:
                districts[d] = {'count': 0, 'sold': 0, 'unsold': 0}
            districts[d]['count'] += 1
            districts[d]['sold'] += int(p.get('houseSoldNum', 0) or 0)
            districts[d]['unsold'] += int(p.get('houseUnsaleNum', 0) or 0)

        result = {
            'code': 1,
            'total': len(all_projects),
            'districts': districts,
            'time': datetime.now().isoformat(),
            'source': 'ygjy'
        }

        cache_set(cache_key, result, ttl_minutes=30)
        return jsonify(result)
    except Exception as e:
        # 用静态数据兜底
        districts = {}
        for p in PROJECTS_CACHE:
            d = parse_district(p.get('projectAddress', ''))
            if d not in districts:
                districts[d] = {'count': 0, 'sold': 0, 'unsold': 0}
            districts[d]['count'] += 1
            districts[d]['sold'] += int(p.get('houseSoldNum', 0) or 0)
            districts[d]['unsold'] += int(p.get('houseUnsaleNum', 0) or 0)

        result = {
            'code': 1,
            'total': len(PROJECTS_CACHE),
            'districts': districts,
            'time': datetime.now().isoformat(),
            'source': 'static'
        }
        return jsonify(result)


@app.route('/api/signing/daily')
def signing_daily():
    """
    每日签约数据 - 核心产品价值
    调用 mrxjspfqyxx.ashx 获取各区当日签约统计
    缓存1小时（因为是日频数据）
    """
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('pageSize', 50)), 100)
    cache_key = f"signing_daily_{page}_{page_size}"

    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        data = call_api('mrxjspfqyxx.ashx', {
            'page': page,
            'pageSize': page_size
        })

        signing_data = data.get('data', [])
        total = data.get('total', 0)

        # 汇总今日签约数
        today_total = 0
        for item in signing_data:
            today_total += int(item.get('signNum', 0) or 0)

        result = {
            'code': 1,
            'data': signing_data,
            'total': total,
            'todaySignedCount': today_total,
            'page': page,
            'pageSize': page_size,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'source': 'ygjy'
        }

        # 每日数据缓存1小时
        cache_set(cache_key, result, ttl_minutes=60)
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)}), 500


# ============== 启动 ==============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print("广州楼盘网签查询 - 统一生产服务器")
    print(f"服务地址: http://0.0.0.0:{port}")
    print(f"静态数据: {len(PROJECTS_CACHE)} 条楼盘")
    print(f"MongoDB: {'已配置' if MONGO_URI else '未配置（仅静态模式）'}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
