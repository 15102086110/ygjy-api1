FROM python:3.11-slim

WORKDIR /app

# 安装依赖（利用缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# Railway 自动注入 PORT 环境变量，gunicorn 监听该端口
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:${PORT:-5001} --workers 2"]
