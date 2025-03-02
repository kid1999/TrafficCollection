# 使用官方 Python 基础镜像
FROM python:3.9-slim

LABEL authors="kid1999"

# 设置工作目录
WORKDIR /traffic

# 安装基础依赖和 tshark
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libexpat1 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    wget \
    tshark \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# 复制程序代码
COPY requirements.txt /traffic

# 安装 Python 依赖
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    playwright install chromium

# 设置默认命令
#CMD ["python", "main.py"]
