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
import pymongo

# ============== 配置 ==============
MONGO_URI = "mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0"
YGJY_BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://zfcj.gz.gov.cn/'
}

# ============== Flask ==============
app = Flask(__name__)
db = None

try:
    client = pymongo.MongoClient(MONGO_URI)
    client.admin.command('ping')
    db = client['ygjy_db']
    print("✅ MongoDB Atlas连接成功!")
except Exception as e:
    print(f"❌ MongoDB连接失败: {e}")

# ============== 阳光家缘API ==============
def call_ygjy_api(path, params=None, retry=3):
    url = YGJY_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(url, headers=HEADERS)
    
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2 ** attempt)
            else:
                raise

# ============== API接口 ==============
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "mongodb": "connected" if db is not None else "disconnected"
    })

@app.route('/api/projects', methods=['GET'])
def get_projects():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    keyword = request.args.get('keyword', '')
    year = request.args.get('year', '')
    
    cache_key = f"projects_p{page}_s{page_size}_{keyword}_{year}"
    
    # 查缓存
    if db is not None:
        cached = db.cache.find_one({"_id": cache_key})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            print("  📦 返回缓存数据")
            return jsonify(cached['data'])
    
    # 调用API
    params = {"page": page, "pageSize": page_size}
    
    try:
        result = call_ygjy_api("fdcxmxxlb.ashx", params)
        projects = result.get('data', [])
        
        # 过滤
        if keyword:
            projects = [p for p in projects 
                      if keyword.lower() in p.get('projectName', '').lower()
                      or keyword in p.get('presell', '')
                      or keyword in p.get('developer', '')]
        
        if year:
            projects = [p for p in projects if p.get('presell', '').startswith(str(year))]
        
        # 存缓存
        if db is not None:
            db.cache.replace_one(
                {"_id": cache_key},
                {"_id": cache_key, "data": {"code": 1, "data": projects}, "expireAt": datetime.now() + timedelta(minutes=5)},
                upsert=True
            )
        
        return jsonify({"code": 1, "data": projects})
        
    except Exception as e:
        return jsonify({"code": 0, "message": str(e)}), 500

@app.route('/api/projects/<project_id>/buildings', methods=['GET'])
def get_buildings(project_id):
    presell = request.args.get('presell', '')
    
    if db is not None:
        cached = db.cache.find_one({"_id": f"buildings_{project_id}"})
        if cached and cached.get('expireAt', datetime.min) > datetime.now():
            return jsonify(cached['data'])
    
    try:
        result = call_ygjy_api("xmldxx.ashx", {"sProjectId": project_id, "sPreSellNo": presell})
        
        if db is not None:
            db.cache.replace_one(
                {"_id": f"buildings_{project_id}"},
                {"_id": f"buildings_{project_id}", "data": result, "expireAt": datetime.now() + timedelta(hours=1)},
                upsert=True
            )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"code": 0, "message": str(e)}), 500

@app.route('/api/buildings/<building_id>/units', methods=['GET'])
def get_units(building_id):
    house_function = int(request.args.get('houseFunction', 0))
    house_status = int(request.args.get('houseStatus', 0))
    
    try:
        result = call_ygjy_api("xmxkbxx.ashx", {
            "buildingId": building_id,
            "houseFunctionId": house_function,
            "houseStatusId": house_status
        })
        
        # 统计
        stats = {"unsold": 0, "signed": 0, "locked": 0}
        if 'data' in result:
            for group in result['data']:
                for unit in group.get('groupData', []):
                    status = unit.get('status', 0)
                    if status == 1:
                        stats['unsold'] += 1
                    elif status == 2:
                        stats['signed'] += 1
                    elif status == 3:
                        stats['locked'] += 1
        
        return jsonify({"code": 1, "data": result.get('data', []), "stats": stats})
    except Exception as e:
        return jsonify({"code": 0, "message": str(e)}), 500

# ============== 主程序 ==============
if __name__ == '__main__':
    print("=" * 50)
    print("广州楼盘网签查询 - 后端API服务")
    print("服务地址: http://localhost:5001")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=False)