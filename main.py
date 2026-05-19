#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广州楼盘网签查询 - 后端API服务（静态数据版）
数据来源：阳光家缘（预抓取，内置在代码中）
支持：预售证/推广名搜索，按年份筛选
"""
import os
import json
import urllib.parse
from flask import Flask, jsonify, request
import pymongo
from datetime import datetime

app = Flask(__name__)
app.json.ensure_ascii = False

# MongoDB配置（可选，用于缓存楼栋/单元数据）
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0'
)

# ============ 内置楼盘数据（从 projects_2019_2026.json 加载）============
PROJECTS_CACHE = []

def load_projects():
    """启动时加载楼盘数据"""
    global PROJECTS_CACHE
    try:
        # 尝试从同级目录的JSON文件加载
        import pathlib
        json_path = pathlib.Path(__file__).parent / 'projects_2019_2026.json'
        if json_path.exists():
            with open(json_path, encoding='utf-8') as f:
                PROJECTS_CACHE = json.load(f)
            print(f"✅ 已从JSON加载 {len(PROJECTS_CACHE)} 个楼盘")
            return
    except Exception as e:
        print(f"⚠️  加载JSON失败: {e}")

    # 兜底：内置少量示例数据
    print("⚠️  使用内置示例数据")
    PROJECTS_CACHE = [
        {'projectId': 'demo1', 'projectName': '示例楼盘A', 'presell': '20240001',
         'developer': '示例开发商', 'houseSoldNum': 50, 'houseUnsaleNum': 100, 'year': 2024},
    ]

load_projects()


# ============ 工具函数 ============
def filter_by_keyword(projects, keyword):
    """按关键词过滤（推广名/预售证/开发商）"""
    kw = keyword.lower()
    return [
        p for p in projects
        if kw in (p.get('projectName') or '').lower()
        or kw in (p.get('presell') or '').lower()
        or kw in (p.get('developer') or '').lower()
    ]

def filter_by_year(projects, year):
    """按年份过滤"""
    if not year:
        return projects
    return [p for p in projects if str(p.get('year')) == str(year)]


# ============ 路由 ============
@app.route('/')
def index():
    return jsonify({
        'name': '广州楼盘网签查询API',
        'version': '3.0.0',
        'dataSource': f'内置数据 {len(PROJECTS_CACHE)} 条（2019-2026）',
        'endpoints': [
            '/api/health',
            '/api/projects',
            '/api/projects/<id>',
            '/api/projects/<id>/buildings',
            '/api/buildings/<id>/units',
            '/api/search',
            '/api/stats',
        ]
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'dataCount': len(PROJECTS_CACHE),
        'mongodb': 'connected' if False else 'not_used',
        'time': datetime.now().isoformat()
    })

@app.route('/api/projects')
def get_projects():
    """获取楼盘列表（支持年份筛选 + 关键词搜索 + 分页）"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('pageSize', 20)), 100)
    year = request.args.get('year', '')
    keyword = request.args.get('keyword', '')

    result = PROJECTS_CACHE

    # 年份筛选
    result = filter_by_year(result, year)

    # 关键词搜索
    if keyword:
        result = filter_by_keyword(result, keyword)

    # 按网签量排序（降序）
    result = sorted(result, key=lambda x: int(x.get('houseSoldNum', 0) or 0), reverse=True)

    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        'data': result[start:end],
        'total': total,
        'page': page,
        'pageSize': page_size,
        'year': year,
        'keyword': keyword
    })

@app.route('/api/search')
def search():
    """搜索（预售证/推广名）"""
    keyword = request.args.get('keyword', '')
    year = request.args.get('year', '')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('pageSize', 20)), 100)

    if not keyword:
        return jsonify({'error': 'keyword required', 'data': []}), 400

    result = PROJECTS_CACHE
    result = filter_by_year(result, year)
    result = filter_by_keyword(result, keyword)
    result = sorted(result, key=lambda x: int(x.get('houseSoldNum', 0) or 0), reverse=True)

    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        'data': result[start:end],
        'total': total,
        'keyword': keyword,
        'year': year
    })

@app.route('/api/stats')
def stats():
    """统计信息"""
    total_sold = sum(int(p.get('houseSoldNum', 0) or 0) for p in PROJECTS_CACHE)
    total_unsale = sum(int(p.get('houseUnsaleNum', 0) or 0) for p in PROJECTS_CACHE)

    year_stats = {}
    for p in PROJECTS_CACHE:
        y = p.get('year', 0)
        if y:
            year_stats[y] = year_stats.get(y, 0) + 1

    return jsonify({
        'totalProjects': len(PROJECTS_CACHE),
        'totalSold': total_sold,
        'totalUnsale': total_unsale,
        'byYear': dict(sorted(year_stats.items()))
    })

@app.route('/api/projects/<project_id>')
def get_project(project_id):
    """楼盘详情"""
    for p in PROJECTS_CACHE:
        if p.get('projectId') == project_id:
            return jsonify(p)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/projects/<project_id>/buildings')
def get_buildings(project_id):
    """楼栋列表（暂返回空，需调用阳光家缘详情API）"""
    return jsonify({
        'projectId': project_id,
        'buildings': [],
        'note': '楼栋数据需要实时调用阳光家缘API，当前为静态数据版本'
    })

@app.route('/api/buildings/<building_id>/units')
def get_units(building_id):
    """单元销控（暂返回空）"""
    return jsonify({
        'buildingId': building_id,
        'units': [],
        'note': '单元数据需要实时调用阳光家缘API'
    })

# ============ 启动 ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 启动服务器: http://localhost:{port}")
    print(f"   数据: {len(PROJECTS_CACHE)} 条楼盘")
    app.run(host='0.0.0.0', port=port, debug=True)
