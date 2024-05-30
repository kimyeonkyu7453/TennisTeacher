# 베이스 이미지
FROM node:lts

# 작업 디렉토리 설정
WORKDIR /front

# 필요한 파일 복사
COPY package*.json ./

# npm 설치
RUN npm install --production

# 나머지 소스 코드 복사
COPY . .

# Python 및 필요한 라이브러리 설치
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

# 가상 환경 생성
RUN python3 -m venv /opt/venv

# 가상 환경 활성화 및 라이브러리 설치
RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install opencv-python-headless pandas numpy joblib scikit-learn==1.4.2 Pillow

# 가상 환경을 PATH에 추가
ENV PATH="/opt/venv/bin:$PATH"
ENV POSE_LIB_PATH=/app/openpose/pose_lib/

# openpose 디렉토리의 pose_lib 경로 생성 및 권한 설정
RUN mkdir -p /front/openpose/pose_lib && chmod -R 777 /front/openpose/pose_lib

# 필요한 모델 파일 및 스크립트 복사
COPY openpose/pose_lib/pose_deploy_linevec.prototxt /front/openpose/pose_lib/pose_deploy_linevec.prototxt
COPY openpose/pose_lib/label_encoder_from.pkl /front/openpose/pose_lib/label_encoder_from.pkl
COPY openpose/pose_lib/label_encoder_to.pkl /front/openpose/pose_lib/label_encoder_to.pkl
COPY openpose/pose_lib/tennis_pose_model.pkl /front/openpose/pose_lib/tennis_pose_model.pkl
COPY openpose/pose_lib/segment_* /front/openpose/pose_lib/
COPY openpose/pose_lib/combine_segments.py /front/openpose/pose_lib/
COPY openpose/analyze_video.py /front/openpose/

# 분할된 파일 결합 스크립트 실행 및 권한 설정
RUN python3 /front/openpose/pose_lib/combine_segments.py
RUN chmod -R 777 /front/openpose/pose_lib

# uploads 디렉토리 생성 및 권한 설정
RUN mkdir -p /front/uploads && chmod -R 777 /front/uploads

# 환경 변수 설정
ENV NODE_ENV=production
ENV PORT=8080
ENV UPLOADS_DIR=/front/uploads
ENV OPENPOSE_DIR=/front/openpose

# 포트 설정
EXPOSE 8080

# 서버 시작
CMD ["node", "server.js"]
