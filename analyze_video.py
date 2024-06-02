import os
import cv2
import pandas as pd
import numpy as np
import math
import joblib
import sys
import json
import shutil
import warnings
from jinja2 import Template
from datetime import datetime
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# Ensure the public directory exists
public_dir = "/app/public"
if not os.path.exists(public_dir):
    os.makedirs(public_dir, mode=0o777)

def combine_files(input_pattern='segment_*', output_path='pose_iter_160000.caffemodel'):
    import glob
    if os.path.exists(output_path):
        os.remove(output_path)  # 기존 파일 삭제
    with open(output_path, 'wb') as output_file:
        for file_name in sorted(glob.glob(input_pattern)):
            with open(file_name, 'rb') as input_file:
                output_file.write(input_file.read())
    os.chmod(output_path, 0o777)  # 파일 권한 설정

# 분할된 파일 결합
combine_files(input_pattern='/app/openpose/pose_lib/segment_*', output_path='/app/openpose/pose_lib/pose_iter_160000.caffemodel')

# MPII에서 각 파트 번호, 선으로 연결될 POSE_PAIRS
BODY_PARTS = {"Head": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
              "LShoulder": 5, "LElbow": 6, "LWrist": 7, "RHip": 8, "RKnee": 9,
              "RAnkle": 10, "LHip": 11, "LKnee": 12, "LAnkle": 13, "Chest": 14,
              "Background": 15}

POSE_PAIRS = [["Head", "Neck"], ["Neck", "RShoulder"], ["RShoulder", "RElbow"],
              ["RElbow", "RWrist"], ["Neck", "LShoulder"], ["LShoulder", "LElbow"],
              ["LElbow", "LWrist"], ["Neck", "Chest"], ["Chest", "RHip"], ["RHip", "RKnee"],
              ["RKnee", "RAnkle"], ["Chest", "LHip"], ["LHip", "LKnee"], ["LKnee", "LAnkle"]]

part_names_korean = {
    "Head": "머리",
    "Neck": "목",
    "RShoulder": "오른쪽 어깨",
    "RElbow": "오른쪽 팔꿈치",
    "RWrist": "오른쪽 손목",
    "LShoulder": "왼쪽 어깨",
    "LElbow": "왼쪽 팔꿈치",
    "LWrist": "왼쪽 손목",
    "RHip": "오른쪽 엉덩이",
    "RKnee": "오른쪽 무릎",
    "RAnkle": "오른쪽 발목",
    "LHip": "왼쪽 엉덩이",
    "LKnee": "왼쪽 무릎",
    "LAnkle": "왼쪽 발목",
    "Chest": "가슴",
    "Background": "배경"
}

# 경로 수정 (Linux 경로 사용)
pose_lib_path = "/app/openpose/pose_lib/"
prototxt_path = os.path.join(pose_lib_path, "pose_deploy_linevec.prototxt")
caffemodel_path = os.path.join(pose_lib_path, "pose_iter_160000.caffemodel")

net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)

label_encoder_from_path = os.path.join(pose_lib_path, 'label_encoder_from.pkl')
label_encoder_to_path = os.path.join(pose_lib_path, 'label_encoder_to.pkl')
label_encoder_from = joblib.load(label_encoder_from_path)
label_encoder_to = joblib.load(label_encoder_to_path)

model_path = os.path.join(pose_lib_path, 'tennis_pose_model.pkl')
model = joblib.load(model_path)

def analyze_frame(image):
    height, width = image.shape[:2]
    max_height = 500
    max_width = 500

    if width > height:
        scale = max_width / width
    else:
        scale = max_height / height

    new_width = int(width * scale)
    new_height = int(height * scale)

    image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    imageHeight, imageWidth, _ = image.shape

    inpBlob = cv2.dnn.blobFromImage(image, 1.0 / 255, (imageWidth, imageHeight), (0, 0, 0), swapRB=False, crop=False)
    net.setInput(inpBlob)
    output = net.forward()

    H = output.shape[2]
    W = output.shape[3]
    points = []
    angles = []

    for i in range(len(BODY_PARTS) - 1):
        probMap = output[0, i, :, :]
        minVal, prob, minLoc, point = cv2.minMaxLoc(probMap)
        x = (imageWidth * point[0]) / W
        y = (imageHeight * point[1]) / H

        if prob > 0.1:
            cv2.circle(image, (int(x), int(y)), 3, (0, 255, 255), thickness=-1, lineType=cv2.FILLED)
            cv2.putText(image, "{}".format(i), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, lineType=cv2.LINE_AA)
            points.append((int(x), int(y)))
        else:
            points.append(None)

    for pair in POSE_PAIRS:
        partFrom = pair[0]
        partTo = pair[1]
        idFrom = BODY_PARTS[partFrom]
        idTo = BODY_PARTS[partTo]

        if points[idFrom] and points[idTo]:
            cv2.line(image, points[idFrom], points[idTo], (0, 255, 0), 2)
            dx = points[idTo][0] - points[idFrom][0]
            dy = points[idTo][1] - points[idFrom][1]
            angle = math.degrees(math.atan2(dy, dx))
            angles.append([partFrom, partTo, angle])

    df_angles = pd.DataFrame(angles, columns=["From", "To", "Angle"])
    if df_angles.empty:
        return image, None
    df_angles['From_encoded'] = label_encoder_from.transform(df_angles['From'])
    df_angles['To_encoded'] = label_encoder_to.transform(df_angles['To'])

    predictions = model.predict(df_angles[["From_encoded", "To_encoded", "Angle"]])
    df_angles['IsCorrect'] = predictions

    return image, df_angles

def process_video(video_path):
    # 파일 존재 여부 확인
    if not os.path.exists(video_path):
        print(f"Error: video file does not exist: {video_path}")
        return None, None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return None, None

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    impact_frame_index = frame_count // 2

    current_frame_index = 0
    impact_frame = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if current_frame_index == impact_frame_index:
            impact_frame = frame
            break

        current_frame_index += 1

    cap.release()

    if impact_frame is not None:
        result_image, result_df = analyze_frame(impact_frame)
        if result_df is not None and 'IsCorrect' in result_df.columns:
            print(result_df.head())  # 데이터프레임 내용 출력
            return result_image, result_df
        else:
            print("result_df가 제대로 생성되지 않았거나 IsCorrect 열이 존재하지 않습니다.")
            return None, None
    else:
        print("임팩트 지점 프레임을 추출하지 못했습니다.")
        return None, None

def save_results_to_json(df_angles, output_path="/app/openpose/result.json"):
    results = df_angles.to_dict(orient='records')
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

def calculate_scores(df_angles):
    # 각 부위별 점수를 계산합니다.
    scores = []
    max_angle_deviation = 1  # 한치의 오차라도 있으면 점수를 깎음
    for index, row in df_angles.iterrows():
        if row['IsCorrect'] == 1:  # Correct한 경우
            scores.append(100)
        else:
            angle_deviation = abs(row['Angle'] - 90)  # 90도와의 편차
            score = max(0, 100 - (angle_deviation / max_angle_deviation) * 100)  # 오차가 1도당 100점 감점
            scores.append(score)
    df_angles['Score'] = scores
    total_score = sum(scores) / len(scores)
    return total_score

def save_results_to_html(image, df_angles, feedback_list, output_path="/app/openpose/result.html"):
    import base64
    from io import BytesIO
    from PIL import Image

    _, buffer = cv2.imencode('.jpg', image)
    img_str = base64.b64encode(buffer).decode('utf-8')

    # 현재 날짜를 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d")

    # 점수 계산
    total_score = calculate_scores(df_angles)

    # 도넛 차트 생성
    fig, ax = plt.subplots(figsize=(4, 4))
    wedges, texts, autotexts = ax.pie([total_score, 100-total_score], startangle=90, colors=['#007bff', '#d3d3d3'],
                                      counterclock=False, wedgeprops=dict(width=0.3, edgecolor='white'), autopct='%1.1f%%')
    plt.setp(autotexts, size=12, weight="bold", color="white")
    ax.text(0, 0, f"{total_score:.2f}/100", ha='center', va='center', fontsize=20, color='black')
    plt.savefig('/app/openpose/score_chart.png', bbox_inches='tight', pad_inches=0.1, dpi=100)
    plt.close(fig)

    with open('/app/openpose/score_chart.png', 'rb') as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    html_template = """
    <html>
    <head>
        <title>자세 분석 결과</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; font-weight: bold; }
            .feedback { margin-top: 20px; font-size: 16px; font-weight: bold; }
            .incorrect { color: red; }
            .date { text-align: center; font-size: 20px; margin-top: 20px; }
            h1 { font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 20px; }
            .score { font-size: 24px; font-weight: bold; text-align: center; margin-bottom: 20px; }
            .row { display: flex; justify-content: space-around; align-items: center; }
            .column { flex: 1; text-align: center; }
            table { font-weight: bold; }
            button { margin-top: 20px; }
            .btn-primary { background-color: #007bff; }
            .btn-success { background-color: #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="my-4">자세 분석 결과</h1>
            <div class="score">{{ current_date }}</div>
            <div class="row">
                <div class="column"><img src="data:image/jpeg;base64,{{ img_str }}" alt="Analyzed Frame" class="img-fluid" id="analyzedFrame"/></div>
                <div class="column"><img src="data:image/png;base64,{{ img_base64 }}" alt="Score Chart" class="img-fluid" id="scoreChart"/></div>
            </div>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>From</th>
                        <th>To</th>
                        <th>Angle</th>
                        <th>IsCorrect</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in results %}
                    <tr>
                        <td>{{ row['From'] }}</td>
                        <td>{{ row['To'] }}</td>
                        <td>{{ row['Angle'] }}</td>
                        <td class="{{ 'correct' if row['IsCorrect'] == 1 else 'incorrect' }}">{{ 'Correct' if row['IsCorrect'] == 1 else 'Incorrect' }}</td>
                        <td>{{ row['Score'] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <div class="feedback">
                <h2 class="my-4">피드백</h2>
                {% for feedback in feedback_list %}
                    <p class="incorrect">{{ feedback }}</p>
                {% endfor %}
            </div>

            <button onclick="history.back()" class="btn btn-primary">뒤로가기</button>
            <button onclick="saveResults()" class="btn btn-success">분석결과 저장하기</button>
        </div>

        <script>
            function saveResults() {
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                const analyzedFrame = document.getElementById('analyzedFrame');
                const scoreChart = document.getElementById('scoreChart');
                
                canvas.width = analyzedFrame.width + scoreChart.width;
                canvas.height = Math.max(analyzedFrame.height, scoreChart.height);
                
                context.drawImage(analyzedFrame, 0, 0);
                context.drawImage(scoreChart, analyzedFrame.width, 0);
                
                const link = document.createElement('a');
                link.href = canvas.toDataURL('image/png');
                link.download = 'result.png';
                link.click();
            }
        </script>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(img_str=img_str, results=df_angles.to_dict(orient='records'), feedback_list=feedback_list, current_date=current_date, img_base64=img_base64, total_score=total_score)

    temp_output_path = "/app/openpose/temp_result.html"
    with open(temp_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    shutil.move(temp_output_path, output_path)


video_path = sys.argv[1]
result_image, result_df = process_video(video_path)

feedback_list = []

if result_image is not None and result_df is not None:
    save_results_to_json(result_df, output_path="/app/openpose/result.json")
    incorrect_poses = result_df[result_df['IsCorrect'] == 0]
    if not incorrect_poses.empty:
        for index, row in incorrect_poses.iterrows():
            from_part_korean = part_names_korean[row['From']]
            to_part_korean = part_names_korean[row['To']]
            current_angle = row['Angle']

            if row['From'] == "Chest" and row['To'] == "LHip":
                mean_angle = 77.886546
                if (current_angle < mean_angle):
                    feedback_list.append(f"허리를 좀 더 숙이시오.")
                else:
                    feedback_list.append(f"허리를 좀 더 피시오.")

            elif row['From'] == "Chest" and row['To'] == "RHip":
                mean_angle = 99.894308
                if (current_angle < mean_angle):
                    feedback_list.append(f"허리를 좀 더 숙이시오.")
                else:
                    feedback_list.append(f"허리를 좀 더 피시오.")

            elif row['From'] == "LHip" and row['To'] == "LKnee":
                mean_angle = 75.916891
                if (current_angle < mean_angle):
                    feedback_list.append(f"왼쪽 무릎을 좀 더 피시오.")
                else:
                    feedback_list.append(f" 왼쪽 무릎을 좀 더 구부리시오.")

            elif row['From'] == "LKnee" and row['To'] == "LAnkle":
                mean_angle = 104.983467
                if (current_angle < mean_angle):
                    feedback_list.append(f"왼쪽 무릎을 좀 더 구부리시오.")
                else:
                    feedback_list.append(f"왼쪽 무릎을 좀 더 피시오.")

            elif row['From'] == "Neck" and row['To'] == "RShoulder":
                mean_angle = 115.946267
                if (current_angle < mean_angle):
                    feedback_list.append(f"오른쪽 어깨를 좀 더 피시오.")
                else:
                    feedback_list.append(f"오른쪽 어깨를 좀 더 접으시오.")

            elif row['From'] == "RElbow" and row['To'] == "RWrist":
                mean_angle = 13.692950
                if (current_angle < mean_angle):
                    feedback_list.append(f"오른쪽 손목을 좀 더 내리십시오.")
                else:
                    feedback_list.append(f"오른쪽 손목을 좀 더 올리십시오.")

            elif row['From'] == "RHip" and row['To'] == "RKnee":
                mean_angle = 94.449991
                if (current_angle < mean_angle):
                    feedback_list.append(f"오른쪽 무릎을 좀 더 피시오.")
                else:
                    feedback_list.append(f"오른쪽 무릎을 좀 더 구부리시오.")

            elif row['From'] == "RKnee" and row['To'] == "RAnkle":
                mean_angle = 124.503426
                if (current_angle < mean_angle):
                    feedback_list.append(f"오른쪽 무릎을 좀 더 구부리시오.")
                else:
                    feedback_list.append(f"오른쪽 무릎을 좀 더 피시오.")

            elif row['From'] == "RShoulder" and row['To'] == "RElbow":
                mean_angle = 52.455323
                if (current_angle < mean_angle):
                    feedback_list.append(f"오른쪽 팔을 좀 더 뒤로 당기십시오.")
                else:
                    feedback_list.append(f"오른쪽 팔을 좀 더 앞으로 당기십시오.")
    else:
        feedback_list.append("자세가 완벽합니다!")

    save_results_to_html(result_image, result_df, feedback_list, output_path="/app/openpose/result.html")
    print("분석 결과가 result.json 및 result.html 파일에 저장되었습니다.")
    shutil.copyfile("/app/openpose/result.html", "/app/public/result.html")
else:
    print("임팩트 지점 프레임을 추출하지 못했습니다.")
