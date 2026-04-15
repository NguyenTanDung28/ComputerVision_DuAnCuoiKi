#Đề tài 6: Cảnh báo tài xế ngủ gật qua webcam: Sử dụng Dlib để phát hiện các mốc
#(landmarks) trên khuôn mặt, tính toán tỷ lệ đóng/mở mắt nhằm đưa ra cảnh báo kịp thời.
import cv2 as cv
import mediapipe as mp 
import math
import numpy as np
import time
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from insightface.app import FaceAnalysis
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

#Khởi tạo FastAPI
app = FastAPI(title="Hệ thống cảnh báo ngủ gật cho tài xế")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

#Biến toàn cục lưu trạng thái còi báo động
ALARM_ON = False

#Khởi tạo Mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces = 1,
    refine_landmarks = True,
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5
)

#Khởi tạo Insightface ở GPU
app_gpu = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app_gpu.prepare(ctx_id = 0, det_size = (640, 640))

#Tính toán EAR
#1.Tọa độ 6 điểm chuẩn quanh 2 mắt
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

#2.Hàm tính khoảng cách euclidean giữa 2 điểm
def euclidean_distance(p1, p2):
    return math.sqrt((p1.x -  p2.x) ** 2 + (p1.y - p2.y) ** 2)

#3.Hàm tính EAR
def calculate_ear(landmarks, eye_indices):
    p1 = landmarks[eye_indices[0]]
    p2 = landmarks[eye_indices[1]]
    p3 = landmarks[eye_indices[2]]
    p4 = landmarks[eye_indices[3]]
    p5 = landmarks[eye_indices[4]]
    p6 = landmarks[eye_indices[5]]
    
    vertical_1 = euclidean_distance(p2, p6)
    vertical_2 = euclidean_distance(p3, p5)
    horizontal = euclidean_distance(p1, p4)

    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)

#Tính tỉ lệ mở miệng
#4 điểm mốc viền môi theo chuẩn Mediapipe
MOUTH_INDICES = [78, 308, 13, 14]
def calculate_mar(landmarks, mouth_indices): #mar: Mouth Aspect Ratio - Tỷ lệ mở miệng
    p_left = landmarks[mouth_indices[0]] #Khóe trái
    p_right = landmarks[mouth_indices[1]] #Khóe phải
    p_top = landmarks[mouth_indices[2]] #Môi trên
    p_bottom = landmarks[mouth_indices[3]] #Môi dưới

    #Tính khoảng cách chiều dọc (độ há của miệng)
    vertical = euclidean_distance(p_top, p_bottom)

    #Tính khoảng cách chiều ngang (độ rộng của miệng)
    horizontal = euclidean_distance(p_left, p_right)

    #Tránh lỗi chia cho 0
    if horizontal == 0:
        return 0.0
    
    return vertical / horizontal

#Thuật toán ước lượng tư thế của đầu (HEAD POSE)
def get_head_pose(landmarks, frame_width, frame_height):
    #Tính toán góc xoay của đầu dựa trên thuật toán solvePnP của OpenCV
    #Định nghĩa tọa độ khuôn mặt 3D chuẩn
    model_points = np.array([
        (0.0, 0.0, 0.0), #Chóp mũi
        (0.0, -330.0, -65.0), #Cằm
        (-225.0, 170.0, -135.0), #Khóe mắt trái
        (225.0, 170.0, -135.0), #Khóe mắt phải
        (-150.0, -150.0, -125.0), #Khóe miệng trái
        (150.0, -150.0, -125.0) #Khóe miệng phải 
    ])

    #Lấy tọa độ 2D thực tế tương ứng từ Mediapipe FaceMesh
    image_points = np.array([
        (landmarks[1].x * frame_width, landmarks[1].y * frame_height), #Chóp mũi
        (landmarks[152].x * frame_width, landmarks[152].y * frame_height), #Cằm
        (landmarks[33].x * frame_width, landmarks[33].y * frame_height), #Khóe mắt trái
        (landmarks[263].x * frame_width, landmarks[263].y * frame_height), #Khóe mắt phải
        (landmarks[61].x * frame_width, landmarks[61].y * frame_height), #Khóe miệng trái
        (landmarks[291].x * frame_width, landmarks[291].y * frame_height) #Khóe miệng phải
    ], dtype="double")

    #Giả lập thông số của Camera (Tiêu cự và tâm quang học)
    focal_length = frame_width
    center = (frame_width / 2, frame_height / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    #Giả định ống kính không bị méo (Distortion = 0)
    dist_coeffs = np.zeros((4,1))
    
    #Dùng PnP để tìm góc xoay
    success, rotation_vector, translation_vector = cv.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs, flags=cv.SOLVEPNP_ITERATIVE
    )

    #Chuyển đổi vector xoay thành các góc độ dễ hiểu
    rmat, _ = cv.Rodrigues(rotation_vector)
    angles, _, _, _, _, _ = cv.RQDecomp3x3(rmat)

    pitch = angles[0]   #Góc gật/cúi
    yaw = angles[1]     #Góc quay trái/phải
    roll = angles[2]    #Góc nghiêng đầu

    return pitch, yaw, roll


#===============================================
#HÀM XỬ LÝ VIDEO & LOGIC CẢNH BÁO
#===============================================
def generate_frames():
    global ALARM_ON #Khai báo sử dụng biến toàn cục
    cap = cv.VideoCapture(0)

    #ĐỊHH NGHĨA NGƯỠNG CẢNH BÁO
    EAR_THRESH = 0.18 #Mắt: Dưới 0.18 là nhắm mắt
    MAR_THRESH = 0.55 #Miệng: Trên 0.50 là há to (ngáp)
    PITCH_THRESH = -15 #Góc gật: Dưới -15 độ là gục đầu xuống
    YAW_THRESH = 25 #Góc quay: Quá 25 độ (trái/phải) là ngoái nhìn

    #BỘ ĐẾM THỜI GIAN (Phân biệt vô tình với vi phạm)
    blink_start_time = 0 #Đếm số frame nhắm mắt liên tục
    yawn_start_time = 0 #Đếm số frame ngáp liên tục
    distract_start_time = 0 #Đếm số frame ngoái/gục đầu liên tục
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # frame_counter += 1
            frame = cv.flip(frame, 1) #Lật hình soi gương

            #Đổi hệ màu từ BGR (Chuẩn OpenCv) sang RGB (Chuẩn Mediapipe)
            rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

            #GỌI HÀM TÍNH TOÁN VÀ KIỂM TRA ĐIỀU KIỆN
            results = face_mesh.process(rgb_frame)
            warning_msg = "" #Thông báo cảnh báo

            #Nếu Camera thấy có khuôn mặt
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark

                    #Đo lường 3 chỉ số
                    left_ear = calculate_ear(landmarks, LEFT_EYE_INDICES)
                    right_ear = calculate_ear(landmarks, RIGHT_EYE_INDICES)
                    ear_avg = (left_ear + right_ear) / 2.0

                    mar = calculate_mar(landmarks, MOUTH_INDICES)
                    pitch, yaw, roll = get_head_pose(landmarks, frame.shape[1], frame.shape[0])

                    #In số liệu ra màn hình để test (Có thể bỏ nếu hoàn thiện)
                    cv.putText(frame, f"EAR: {ear_avg:.2f} | MAR: {mar:.2f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    cv.putText(frame, f"Pitch: {pitch:.0f} | Yaw: {yaw:.0f}", (10, 60), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                    #XÉT ĐIỀU KIỆN
                    #1. Chống ngủ gật
                    if ear_avg < EAR_THRESH:
                        if mar < MAR_THRESH:
                            if blink_start_time == 0:
                                blink_start_time = time.time()
                            #Nếu nhắm mắt liên tục quá 5 giây
                            elif time.time() - blink_start_time >= 1.0:
                                warning_msg = "CANH BAO: BAN DANG NGU GAT!"
                                ALARM_ON = True
                    else:
                        blink_start_time = 0 #Reset bộ đếm
                        ALARM_ON = False
                    
                    #2. Chống ngáp ngủ
                    if mar > MAR_THRESH:
                        if yawn_start_time == 0:
                            yawn_start_time = time.time()
                        elif time.time() - yawn_start_time >= 1.5: 
                            warning_msg = "DANG NGAP"
                    else:
                        yawn_start_time = 0

                    #3. Chống mất tập trung
                    if pitch < PITCH_THRESH or abs(yaw) > YAW_THRESH:
                        if distract_start_time == 0:
                            distract_start_time = time.time()
                        elif time.time() - distract_start_time >= 4.0:
                            warning_msg = "DANG MAT TAP TRUNG"
                    else:
                        distract_start_time = 0
            
            #KÍCH HOẠT BÁO ĐỘNG TRÊN MÀN HÌNH
            if warning_msg != "":
                frame_height, frame_width = frame.shape[:2]
                font = cv.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6  # <-- Sửa số này để chỉnh to nhỏ (0.6 là cỡ vừa phải)
                thickness = 2
                color = (0, 0, 255)
                (text_width, text_height), baseline = cv.getTextSize(warning_msg, font, font_scale, thickness)
                margin = 15 # Cách lề 15 pixel cho đỡ sát viền
                x = frame_width - text_width - margin
                y = text_height + margin
                cv.putText(frame, warning_msg, (int(x), int(y)), font, font_scale, color, thickness, cv.LINE_AA)

            _, buffer = cv.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    finally:
        cap.release()


# ==========================================
# CÁC ĐƯỜNG DẪN WEB (API ENDPOINTS)
# ==========================================
from fastapi import Request
from fastapi.responses import StreamingResponse
import uvicorn

# 1. Đường dẫn trang chủ (Gọi file index.html)
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# 2. Đường dẫn truyền Video Stream
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# 3. Đường dẫn gửi trạng thái còi báo động (Không bị thụt lề)
@app.get("/status")
def get_status():
    return JSONResponse({"alarm": ALARM_ON})

# Lệnh khởi động server Web
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)