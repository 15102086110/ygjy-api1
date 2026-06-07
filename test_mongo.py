#!/usr/bin/env python3
"""测试MongoDB连接"""
import pymongo

try:
    client = pymongo.MongoClient('mongodb+srv://tzq_admin:tzq0615@cluster0.0uvs04o.mongodb.net/?appName=Cluster0')
    client.admin.command('ping')
    print('✅ MongoDB Atlas 连接成功!')
except Exception as e:
    print(f'❌ 连接失败: {e}')
