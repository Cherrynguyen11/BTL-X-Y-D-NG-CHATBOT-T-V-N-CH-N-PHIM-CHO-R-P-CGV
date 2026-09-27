import uvicorn
import os
import sys

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 65)
    print("CGV CINEMAS AI ASSISTANT - TRỢ LÝ ĐIỆN ẢNH THÔNG MINH")
    print("Dự án BTL Trí Tuệ Nhân Tạo (NLP, Recommendation, Hybrid RAG)")
    print("Đang khởi chạy máy chủ tại: http://localhost:8000")
    print("Tài liệu API Swagger UI tại: http://localhost:8000/docs")
    print("=" * 65)
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
