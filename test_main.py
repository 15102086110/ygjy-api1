#!/usr/bin/env python3
"""测试修复后的main.py"""
import sys
sys.path.insert(0, '/Users/mac/Desktop/guangzhou_property')

import main
print('✅ main.py 导入成功')
print('  BASE:', main.BASE)
print('  HEADERS keys:', list(main.HEADERS.keys()))

# 测试call_api
print('\n测试 call_api...')
result = main.call_api('fdcxmxxlb.ashx', {'page': 1, 'pageSize': 3})
print(f'  返回 {len(result.get("data", []))} 条')
