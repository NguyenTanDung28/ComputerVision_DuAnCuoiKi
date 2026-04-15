import onnxruntime as ort

print("Đang kiểm tra kết nối GPU...")
providers = ort.get_available_providers()
print("Các bộ xử lý khả dụng:", providers)

if 'CUDAExecutionProvider' in providers:
    print("✅ TUYỆT VỜI! Hệ thống ĐÃ nhận diện được GPU NVIDIA (RTX 3050).")
else:
    print("❌ LỖI: Hệ thống chỉ nhận CPU. Chúng ta cần cài thêm CUDA Toolkit.")