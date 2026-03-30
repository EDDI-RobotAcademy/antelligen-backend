# 1. uv 바이너리 가져오기
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.13-slim

# 2. uv 및 필수 도구 설정
COPY --from=uv_bin /uv /bin/uv
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. uv를 이용한 광속 패키지 설치
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

# 4. 실행
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]