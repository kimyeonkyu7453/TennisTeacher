#!/bin/bash

# 업로드 디렉토리 및 openpose 디렉토리 권한 설정
chmod -R 777 /front/uploads
chmod -R 777 /front/openpose/pose_lib

# 서버 시작
exec "$@"
