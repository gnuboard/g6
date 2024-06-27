# 최신 Python 이미지 사용
FROM python:3.12.1-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 파일 복사
COPY . .

# FastAPI 실행 명령
CMD ["uvicorn", "main:app", "--reload","--host", "0.0.0.0", "--port", "8000"]