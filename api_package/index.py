#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广州楼盘网签查询 - 后端API服务
阳光家缘数据API + MongoDB缓存
"""
import urllib.request
import urllib.parse
import json
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

# MongoDB Atlas连接（从环境变量读取）
import os
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0')

# 全局数据库连接
db = None

def get_db():
    """获取数据库连接（延迟初始化）"""
    global db
    if db is None:
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            db = client['ygjy_db']
            print("MongoDB Atlas连接成功")
        except Exception as e:
            print(f"MongoDB连接失败: {e}")
            db = None
    return db

# 阳光家缘API基础地址
BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

# 请求头（模拟浏览器）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

def call_api(path, params=None, max_retry=3):
    """调用阳光家缘API（带重试）"""
    url = BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, headers=HEADERS)
    
    for attempt in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(3 * (attempt + 1))  # 指数退避: 3s, 6s, 9s
            else:
                raise e

def parse_district(address):
    """从地址提取行政区"""
    districts = ['天河区', '海珠区', '荔湾区', '越秀区', '白云区', '黄埔区', '番禺区', '南沙区', '花都区', '增城区', '从化区']
    for d in districts:
        if d in address:
            return d
    return '未知'

# ========== API路由 ==========

@app.route('/')
def index():
    """首页"""
    return jsonify({
        'name': '广州楼盘网签查询API',
        'version': '1.0.0',
        'endpoints': [
            '/api/health - 健康检查',
            '/api/projects - 楼盘列表',
            '/api/projects/<id>/buildings - 楼栋列表',
            '/api/buildings/<id>/units - 单元销控',
            '/api/search?q=关键词 - 搜索楼盘'
        ]
    })

@app.route('/api/health')
def health():
    """健康检查"""
    db_ok = False
    if get_db() is not None:
        try:
            db.command('ping')
            db_ok = True
        except:
            pass
    
    return jsonify({
        'status': 'ok',
        'mongodb': 'connected' if db_ok else 'disconnected',
        'time': datetime.now().isoformat()
    })

@app.route('/api/projects')
def get_projects():
    """获取楼盘列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('pageSize', 20)), 50)
    district = request.args.get('district', '')
    year = request.args.get('year', '')
    
    cache_key = f"projects_{page}_{page_size}_{district}_{year}"
    database = get_db()
    
    # 先查缓存（5分钟有效）
    if database is not None:
        cached = database.cache.find_one({"_id": cache_key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return jsonify(cached['data'])
    
    try:
        # 调用阳光家缘API
        params = {'page': page, 'pageSize': page_size}
        data = call_api('fdcxmxxlb.ashx', params)
        
        # 处理数据
        projects = data.get('data', [])
        total = data.get('total', 0)
        
        # 过滤行政区
        if district:
            projects = [p for p in projects if district in p.get('projectAddress', '')]
        
        # 过滤年份
        if year:
            projects = [p for p in projects if p.get('presell', '').startswith(year)]
        
        result = {
            'code': 1,
            'data': projects,
            'total': total,
            'page': page,
            'pageSize': page_size,
            'source': 'ygjy'
        }
        
        # 存入缓存
        if database is not None:
            database.cache.replace_one(
                {"_id": cache_key},
                {
                    "_id": cache_key,
                    "data": result,
                    "expireAt": datetime.now() + timedelta(minutes=5)
                },
                upsert=True
            )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)})

@app.route('/api/projects/<project_id>/buildings')
def get_buildings(project_id):
    """获取楼栋列表"""
    database = get_db()
    
    cache_key = f"buildings_{project_id}"
    
    # 先查缓存（10分钟有效）
    if database is not None:
        cached = database.cache.find_one({"_id": cache_key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return jsonify(cached['data'])
    
    try:
        data = call_api('xmldxx.ashx', {'sProjectId': project_id})
        buildings = data.get('data', [])
        
        result = {'code': 1, 'data': buildings}
        
        # 存入缓存
        if database is not None:
            database.cache.replace_one(
                {"_id": cache_key},
                {
                    "_id": cache_key,
                    "data": result,
                    "expireAt": datetime.now() + timedelta(minutes=10)
                },
                upsert=True
            )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)})

@app.route('/api/buildings/<building_id>/units')
def get_units(building_id):
    """获取单元销控数据"""
    database = get_db()
    house_function = request.args.get('houseFunctionId', '0')
    house_status = request.args.get('houseStatusId', '0')
    
    cache_key = f"units_{building_id}_{house_function}_{house_status}"
    
    # 先查缓存（5分钟有效）
    if database is not None:
        cached = database.cache.find_one({"_id": cache_key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return jsonify(cached['data'])
    
    try:
        data = call_api('xmxkbxx.ashx', {
            'buildingId': building_id,
            'houseFunctionId': house_function,
            'houseStatusId': house_status
        })
        
        # 统计各状态数量
        stats = {'unsold': 0, 'signed': 0, 'locked': 0, 'total': 0}
        units_list = []
        
        groups = data.get('data', [])
        for group in groups:
            floor_num = group.get('floorNum', '')
            for unit in group.get('groupData', []):
                status = unit.get('status', 1)
                if status == 1:
                    stats['unsold'] += 1
                elif status == 2:
                    stats['signed'] += 1
                elif status == 3:
                    stats['locked'] += 1
                stats['total'] += 1
                units_list.append({
                    'unitId': unit.get('unitId', ''),
                    'unitNum': unit.get('unitNum', ''),
                    'floorNum': floor_num,
                    'houseFunction': unit.get('houseFunction', ''),
                    'totalArea': unit.get('totalArea', 0),
                    'inArea': unit.get('inArea', 0),
                    'status': status,
                    'pledgeStatus': unit.get('pledgeStatus', 0)
                })
        
        result = {
            'code': 1,
            'data': units_list,
            'stats': stats,
            'buildingId': building_id
        }
        
        # 存入缓存
        if database is not None:
            database.cache.replace_one(
                {"_id": cache_key},
                {
                    "_id": cache_key,
                    "data": result,
                    "expireAt": datetime.now() + timedelta(minutes=5)
                },
                upsert=True
            )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)})

@app.route('/api/search')
def search():
    """搜索楼盘"""
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'code': 0, 'error': '缺少关键词参数q'})
    
    # 使用楼盘列表API搜索
    try:
        # 先获取足够多的数据
        all_projects = []
        page = 1
        
        while len(all_projects) < 200:  # 最多搜2000条
            data = call_api('fdcxmxxlb.ashx', {'page': page, 'pageSize': 50})
            projects = data.get('data', [])
            if not projects:
                break
            all_projects.extend(projects)
            page += 1
            time.sleep(0.3)
        
        # 关键词匹配
        results = [
            p for p in all_projects
            if keyword in p.get('projectName', '') 
            or keyword in p.get('presell', '')
            or keyword in p.get('developer', '')
        ]
        
        return jsonify({
            'code': 1,
            'keyword': keyword,
            'count': len(results),
            'data': results[:50]  # 最多返回50条
        })
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)})

@app.route('/api/stats')
def stats():
    """获取统计信息（各区楼盘数量）"""
    database = get_db()
    
    cache_key = "stats_districts"
    
    # 先查缓存（30分钟有效）
    if database is not None:
        cached = database.cache.find_one({"_id": cache_key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return jsonify(cached['data'])
    
    try:
        # 获取所有楼盘统计
        all_projects = []
        page = 1
        
        while page <= 20:  # 最多20页1000条
            data = call_api('fdcxmxxlb.ashx', {'page': page, 'pageSize': 50})
            projects = data.get('data', [])
            if not projects:
                break
            all_projects.extend(projects)
            page += 1
            time.sleep(0.3)
        
        # 统计各区
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
            'time': datetime.now().isoformat()
        }
        
        # 存入缓存
        if database is not None:
            database.cache.replace_one(
                {"_id": cache_key},
                {
                    "_id": cache_key,
                    "data": result,
                    "expireAt": datetime.now() + timedelta(minutes=30)
                },
                upsert=True
            )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'code': 0, 'error': str(e)})

# ========== 启动 ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)