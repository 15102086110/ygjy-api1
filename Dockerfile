FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# Railway 注入的 PORT 环境变量
EXPOSE $PORT

# 启动命令
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:$PORT", "--workers", "2"]
