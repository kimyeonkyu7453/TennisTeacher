import sys
import cv2
import os

def resize_video(input_path, output_path, width=320, height=240, bitrate=500):
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        print(f"Error opening video file: {input_path}")
        return
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, cap.get(cv2.CAP_PROP_FPS), (width, height), isColor=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        resized_frame = cv2.resize(frame, (width, height))
        out.write(resized_frame)
    
    cap.release()
    out.release()
    
    # ffmpeg를 사용하여 비트레이트를 낮추어 재인코딩합니다.
    command = f"ffmpeg -i {output_path} -vf scale={width}:{height} -c:v libx264 -preset fast -crf 28 {output_path.replace('.mp4', '_low.mp4')}"
    result = os.system(command)
    
    if result == 0:
        os.remove(output_path)  # 원본 파일 삭제
        os.rename(output_path.replace('.mp4', '_low.mp4'), output_path)  # 파일명 변경
        print(f"Resized and re-encoded video saved to: {output_path}")
    else:
        print("Error re-encoding video")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python resize_video.py <input_path> <output_path>")
    else:
        resize_video(sys.argv[1], sys.argv[2])
