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

# PYTHONPATH 지정 (루트 전체)
ENV PYTHONPATH=/app

EXPOSE 33333

# MySQL, Redis, PostgreSQL 모두 준비된 후 실행
CMD ["/wait-for-it.sh", "mysql:3306", "--", \
     "/wait-for-it.sh", "redis:6379", "--", \
     "/wait-for-it.sh", "postgres:5432", "--", \
     "python", "-m", "main"]
