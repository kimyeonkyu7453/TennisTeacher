# 베이스 이미지로 python:3.9-slim-buster 사용
FROM python:3.9-slim-buster

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# UID와 GID 설정
ARG UID=1000
ARG GID=1000

# python 유저 생성 및 설정
RUN groupadd -g "${GID}" python \
  && useradd --create-home --no-log-init -u "${UID}" -g "${GID}" python

# 작업 디렉토리 설정
WORKDIR /app

# Node.js 18.x 및 ffmpeg 설치
RUN apt-get update && \
    apt-get install -y python3-pip python3-dev cmake build-essential curl ffmpeg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# npm 최신 버전 설치
RUN npm install -g npm@latest

# Python 패키지 설치
RUN pip3 install --upgrade pip && \
    pip3 install opencv-python-headless pandas numpy joblib scikit-learn==1.4.2 Pillow matplotlib jinja2

# 앱의 종속성 설치
COPY package*.json ./
RUN npm install

# 애플리케이션 소스 코드 복사
COPY . .

# 업로드 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/uploads && chmod -R 777 /app/uploads

# openpose 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/openpose/pose_lib && chmod -R 777 /app/openpose
COPY analyze_video.py /app/openpose/analyze_video.py
COPY openpose/pose_lib /app/openpose/pose_lib/

# public 디렉토리 복사 및 권한 설정
COPY public /app/public/
RUN chown -R python:python /app/public && chmod -R 777 /app/public

# USER 변경은 반드시 pip 패키지 설치 스크립트 이후에 작성되어야 함
USER python:python

# PATH 환경 변수 설정
ENV PATH="/home/python/.local/bin:${PATH}"

# 컨테이너에서 사용할 포트 지정
EXPOSE 8080

# 서버 실행
CMD ["node", "/app/server.js"]

