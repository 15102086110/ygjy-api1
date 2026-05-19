#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广州楼盘网签查询 - 后端API服务
阳光家缘数据API + MongoDB缓存
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

# MongoDB配置 - 从环境变量读取
MONGO_URI = os.environ.get("MONGO_URI", "")

# 阳光家缘API基础地址
BASE = "https://zfcj.gz.gov.cn/ysqgk/Api/WebApi/"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://zfcj.gz.gov.cn/zfcj/fyxx/projectdetail/index.html",
}

# MongoDB连接
db = None
if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client["ygjy_db"]
        print("MongoDB connected")
    except Exception as e:
        print(f"MongoDB error: {e}")
else:
    print("No MONGO_URI set, running without database")

def call_api(path, params=None, retry=3):
    """调用阳光家缘API（带重试）"""
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=HEADERS)
    
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retry - 1:
                print(f"API error: {e}")
                return {"data": [], "total": 0}
            time.sleep(2 * (attempt + 1))

@app.route("/")
def index():
    """首页"""
    return jsonify({
        "name": "广州楼盘网签查询API",
        "version": "1.0.0",
        "endpoints": [
            "/api/health",
            "/api/projects",
            "/api/projects/<id>",
            "/api/projects/<id>/buildings",
            "/api/buildings/<id>/units"
        ]
    })

@app.route("/api/health")
def health():
    """健康检查"""
    mongodb_status = "connected" if db is not None else "disconnected"
    return jsonify({
        "status": "ok",
        "mongodb": mongodb_status,
        "time": datetime.now().isoformat()
    })

@app.route("/api/projects")
def get_projects():
    """获取楼盘列表"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))
    keyword = request.args.get("keyword", "")
    
    data = call_api("fdcxmxxlb.ashx", {
        "page": page,
        "pageSize": page_size
    })
    
    projects = data.get("data", [])
    
    # 关键词过滤
    if keyword:
        projects = [p for p in projects 
                   if keyword in p.get("projectName", "") 
                   or keyword in p.get("presell", "")]
    
    return jsonify({
        "data": projects,
        "total": len(projects),
        "page": page,
        "pageSize": page_size
    })

@app.route("/api/projects/<project_id>")
def get_project(project_id):
    """获取单个楼盘详情"""
    data = call_api("fdcxmxxlb.ashx", {"page": 1, "pageSize": 50})
    
    projects = data.get("data", [])
    project = next((p for p in projects if p.get("projectId") == project_id), None)
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    return jsonify(project)

@app.route("/api/projects/<project_id>/buildings")
def get_buildings(project_id):
    """获取楼盘的楼栋列表"""
    data = call_api("fdcxmxxlb.ashx", {"page": 1, "pageSize": 50})
    projects = data.get("data", [])
    project = next((p for p in projects if p.get("projectId") == project_id), None)
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    presell = project.get("presell", "")
    
    if presell:
        building_data = call_api("xmldxx.ashx", {
            "sProjectId": project_id,
            "sPreSellNo": presell
        })
    else:
        building_data = {"data": []}
    
    return jsonify({
        "data": building_data.get("data", []),
        "projectName": project.get("projectName", "")
    })

@app.route("/api/buildings/<building_id>/units")
def get_units(building_id):
    """获取楼栋的单元销控"""
    data = call_api("xmxkbxx.ashx", {
        "buildingId": building_id,
        "houseFunctionId": 0,
        "houseStatusId": 0
    })
    
    stats = {"unsold": 0, "signed": 0, "locked": 0}
    units = []
    
    for group in data.get("data", []):
        for unit in group.get("groupData", []):
            status = unit.get("status", 0)
            if status == 1:
                stats["unsold"] += 1
            elif status == 2:
                stats["signed"] += 1
            elif status == 3:
                stats["locked"] += 1
            units.append(unit)
    
    return jsonify({
        "units": units,
        "stats": stats,
        "total": len(units)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
