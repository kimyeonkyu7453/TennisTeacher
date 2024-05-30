import cv2
import pandas as pd
import numpy as np
import math
import os
import joblib
import sys
import json
import shutil

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
combine_files(input_pattern='/front/openpose/pose_lib/segment_*', output_path='/front/openpose/pose_lib/pose_iter_160000.caffemodel')

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
pose_lib_path = "/front/openpose/pose_lib/"
prototxt_path = os.path.join(pose_lib_path, "pose_deploy_linevec.prototxt")
caffemodel_path = os.path.join(pose_lib_path, "pose_iter_160000.caffemodel")

# 모델 파일 권한 설정
os.chmod(prototxt_path, 0o777)
os.chmod(caffemodel_path, 0o777)

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
    df_angles['From_encoded'] = label_encoder_from.transform(df_angles['From'])
    df_angles['To_encoded'] = label_encoder_to.transform(df_angles['To'])

    predictions = model.predict(df_angles[["From_encoded", "To_encoded", "Angle"]])
    df_angles['IsCorrect'] = predictions

    return image, df_angles

def process_video(video_path):
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
        return result_image, result_df
    else:
        return None, None

def save_results_to_json(df_angles, output_path="/front/openpose/result.json"):
    results = df_angles.to_dict(orient='records')
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

def save_results_to_html(image, df_angles, output_path="/front/openpose/result.html"):
    import base64
    from io import BytesIO
    from PIL import Image

    _, buffer = cv2.imencode('.jpg', image)
    img_str = base64.b64encode(buffer).decode('utf-8')

    html_content = f"""
    <html>
    <head>
        <title>분석 결과</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>테니스 자세 분석 결과</h1>
        <img src="data:image/jpeg;base64,{img_str}" alt="Analyzed Frame" style="max-width:100%;height:auto;"/>

        <h2>자세 분석 결과</h2>
        <table>
            <tr>
                <th>From</th>
                <th>To</th>
                <th>Angle</th>
                <th>IsCorrect</th>
            </tr>
    """

    for _, row in df_angles.iterrows():
        html_content += f"""
            <tr>
                <td>{row['From']}</td>
                <td>{row['To']}</td>
                <td>{row['Angle']:.2f}</td>
                <td>{'Correct' if row['IsCorrect'] == 1 else 'Incorrect'}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

video_path = sys.argv[1]
result_image, result_df = process_video(video_path)

if result_image is not None and result_df is not None:
    save_results_to_json(result_df, output_path="/front/openpose/result.json")
    save_results_to_html(result_image, result_df, output_path="/front/openpose/result.html")
    print("분석 결과가 result.json 및 result.html 파일에 저장되었습니다.")
    shutil.copy("/front/openpose/result.html", "/front/public/result.html")
else:
    print("임팩트 지점 프레임을 추출하지 못했습니다.")

incorrect_poses = result_df[result_df['IsCorrect'] == 0]
if not incorrect_poses.empty:
    print("잘못된 자세:")
    for index, row in incorrect_poses.iterrows():
        from_part_korean = part_names_korean[row['From']]
        to_part_korean = part_names_korean[row['To']]
        current_angle = row['Angle']

        if row['From'] == "Chest" and row['To'] == "LHip":
            mean_angle = 77.886546
            if current_angle < mean_angle:
                print(f"허리를 좀 더 숙이시오.")
            else:
                print(f"허리를 좀 더 피시오.")

        elif row['From'] == "Chest" and row['To'] == "RHip":
            mean_angle = 99.894308
            if current_angle < mean_angle:
                print(f"허리를 좀 더 숙이시오.")
            else:
                print(f"허리를 좀 더 피시오.")

        elif row['From'] == "LHip" and row['To'] == "LKnee":
            mean_angle = 75.916891
            if current_angle < mean_angle:
                print(f"왼쪽 무릎을 좀 더 피시오.")
            else:
                print(f" 왼쪽 무릎을 좀 더 구부리시오.")

        elif row['From'] == "LKnee" and row['To'] == "LAnkle":
            mean_angle = 104.983467
            if current_angle < mean_angle:
                print(f"왼쪽 무릎을 좀 더 구부리시오.")
            else:
                print(f"왼쪽 무릎을 좀 더 피시오.")

        elif row['From'] == "Neck" and row['To'] == "RShoulder":
            mean_angle = 115.946267
            if current_angle < mean_angle:
                print(f"오른쪽 어깨를 좀 더 피시오.")
            else:
                print(f"오른쪽 어깨를 좀 더 접으시오.")

        elif row['From'] == "RElbow" and row['To'] == "RWrist":
            mean_angle = 13.692950
            if current_angle < mean_angle:
                print(f"오른쪽 손목을 좀 더 내리십시오.")
            else:
                print(f"오른쪽 손목을 좀 더 올리십시오.")

        elif row['From'] == "RHip" and row['To'] == "RKnee":
            mean_angle = 94.449991
            if current_angle < mean_angle:
                print(f"오른쪽 무릎을 좀 더 피시오.")
            else:
                print(f"오른쪽 무릎을 좀 더 구부리시오.")

        elif row['From'] == "RKnee" and row['To'] == "RAnkle":
            mean_angle = 124.503426
            if current_angle < mean_angle:
                print(f"오른쪽 무릎을 좀 더 구부리시오.")
            else:
                print(f"오른쪽 무릎을 좀 더 피시오.")

        elif row['From'] == "RShoulder" and row['To'] == "RElbow":
            mean_angle = 52.455323
            if current_angle < mean_angle:
                print(f"오른쪽 팔을 좀 더 뒤로 당기십시오.")
            else:
                print(f"오른쪽 팔을 좀 더 앞으로 당기십시오.")
else:
    print("자세가 완벽합니다!")

