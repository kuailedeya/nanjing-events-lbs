# ==============================================================================
# Nanjing LBS & Social Intelligence Platform - Production Dockerfile
# ==============================================================================
FROM python:3.11-slim

# 设置工作目录与环境变量
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8765 \
    TZ=Asia/Shanghai

# 安装系统基础库及时区支持
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝核心服务代码及静态资源
COPY dashboard_server.py .
COPY nanjing_lbs_engine.py .
COPY social_obsidian_sync.py .
COPY nanjing_seeds.py .
COPY generate_apple_dashboard.py .
COPY dashboard.html .
COPY local.db .
COPY frontend/dist ./frontend/dist

# 暴露服务端口
EXPOSE 8765

# 启动 LBS 服务端（内置每日 12:00 抓取定时器、WAL 数据库与 Apple 空间看板）
CMD ["python", "dashboard_server.py", "--host", "0.0.0.0", "--port", "8765"]
