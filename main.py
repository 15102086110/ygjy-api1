#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广州楼盘网签查询 - 后端API服务
阳光家缘数据API + MongoDB缓存
支持2019-2026年数据 + 预售证/推广名搜索
"""
import os
import urllib.request
import urllib.parse
import json
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
import pymongo

app = Flask(__name__)

# MongoDB配置
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0')

# 阳光家缘API基础地址
BASE = "https://zfcj.gz.gov.cn/ysqgk/api/WebApi/"

# 请求头（和test_api.py保持一致）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

# MongoDB连接
db = None
try:
    client = pymongo.MongoClient(MONGO_URI)
    client.admin.command('ping')
    db = client['ygjy_db']
    print("✅ MongoDB connected")
except Exception as e:
    print(f"❌ MongoDB error: {e}")

def call_api(path, params=None, retry=3):
    """调用阳光家缘API（带重试）"""
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=HEADERS)
    
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt == retry - 1:
                print(f"API error: {e}")
                return {'data': [], 'total': 0}
            time.sleep(2 * (attempt + 1))

# 缓存数据
_cache = {'projects': None, 'time': 0}
CACHE_TTL = 300  # 5分钟缓存

def get_projects_data(year=None, page=1, page_size=100):
    """获取楼盘数据（带缓存）"""
    # 检查缓存
    now = time.time()
    if _cache['projects'] and (now - _cache['time']) < CACHE_TTL:
        projects = _cache['projects']
    else:
        # 获取所有数据（多页）
        all_projects = []
        for p in range(1, 50):  # 最多获取50页
            data = call_api('fdcxmxxlb.ashx', {'page': p, 'pageSize': 100})
            items = data.get('data', [])
            if not items:
                break
            all_projects.extend(items)
            time.sleep(0.5)  # 避免请求过快
        
        _cache['projects'] = all_projects
        _cache['time'] = now
        projects = all_projects
    
    # 过滤年份
    if year:
        projects = [p for p in projects if str(year) in str(p.get('presell', ''))]
    
    return projects

@app.route('/')
def index():
    """首页"""
    return jsonify({
        'name': '广州楼盘网签查询API',
        'version': '2.0.0',
        'endpoints': [
            '/api/health',
            '/api/projects',
            '/api/projects/<id>',
            '/api/projects/<id>/buildings',
            '/api/buildings/<id>/units',
            '/api/search'  # 新增搜索API
        ]
    })

@app.route('/api/health')
def health():
    """健康检查"""
    mongodb_status = "connected" if db is not None else "disconnected"
    return jsonify({
        'status': 'ok',
        'mongodb': mongodb_status,
        'time': datetime.now().isoformat()
    })

@app.route('/api/projects')
def get_projects():
    """获取楼盘列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    year = request.args.get('year', '')
    keyword = request.args.get('keyword', '')
    
    # 获取数据
    if year:
        projects = get_projects_data(year=int(year) if year.isdigit() else None)
    else:
        projects = get_projects_data()
    
    # 关键词过滤（支持预售证号和推广名）
    if keyword:
        kw = keyword.lower()
        projects = [p for p in projects 
                   if kw in str(p.get('projectName', '')).lower()
                   or kw in str(p.get('presell', '')).lower()
                   or kw in str(p.get('developer', '')).lower()]
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paginated = projects[start:end]
    
    return jsonify({
        'data': paginated,
        'total': len(projects),
        'page': page,
        'pageSize': page_size,
        'year': year
    })

@app.route('/api/search')
def search():
    """搜索API - 支持预售证号和推广名"""
    keyword = request.args.get('keyword', '')
    year = request.args.get('year', '')  # 2019-2026
    page_size = int(request.args.get('pageSize', 50))
    
    if not keyword:
        return jsonify({'error': ' keyword required', 'data': []})
    
    # 获取数据
    if year:
        projects = get_projects_data(year=int(year) if year.isdigit() else None)
    else:
        projects = get_projects_data()
    
    # 搜索匹配
    kw = keyword.lower()
    results = []
    for p in projects:
        project_name = str(p.get('projectName', '')).lower()
        presell = str(p.get('presell', '')).lower()
        developer = str(p.get('developer', '')).lower()
        
        # 精确匹配预售证号
        if kw == presell:
            results.insert(0, p)
        # 模糊匹配
        elif kw in project_name or kw in developer:
            results.append(p)
    
    return jsonify({
        'keyword': keyword,
        'data': results[:page_size],
        'total': len(results),
        'year': year
    })

@app.route('/api/projects/<project_id>')
def get_project(project_id):
    """获取单个楼盘详情"""
    projects = get_projects_data()
    project = next((p for p in projects if p.get('projectId') == project_id), None)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    return jsonify(project)

@app.route('/api/projects/<project_id>/buildings')
def get_buildings(project_id):
    """获取楼盘的楼栋列表"""
    projects = get_projects_data()
    project = next((p for p in projects if p.get('projectId') == project_id), None)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    presell = project.get('presell', '')
    
    if presell:
        building_data = call_api('xmldxx.ashx', {
            'sProjectId': project_id,
            'sPreSellNo': presell
        })
    else:
        building_data = {'data': []}
    
    return jsonify({
        'data': building_data.get('data', []),
        'projectName': project.get('projectName', '')
    })

@app.route('/api/buildings/<building_id>/units')
def get_units(building_id):
    """获取楼栋的单元销控"""
    data = call_api('xmxkbxx.ashx', {
        'buildingId': building_id,
        'houseFunctionId': 0,
        'houseStatusId': 0
    })
    
    stats = {'unsold': 0, 'signed': 0, 'locked': 0}
    units = []
    
    for group in data.get('data', []):
        for unit in group.get('groupData', []):
            status = unit.get('status', 0)
            if status == 1:
                stats['unsold'] += 1
            elif status == 2:
                stats['signed'] += 1
            elif status == 3:
                stats['locked'] += 1
            units.append(unit)
    
    return jsonify({
        'units': units,
        'stats': stats,
        'total': len(units)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)