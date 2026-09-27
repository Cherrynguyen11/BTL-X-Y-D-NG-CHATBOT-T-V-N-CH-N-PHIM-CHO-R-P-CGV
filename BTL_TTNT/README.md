# BÀI TẬP LỚN TRÍ TUỆ NHÂN TẠO (AI): CHATBOT TƯ VẤN PHIM CGV CINEMAS

Hệ thống **Chatbot AI Tư Vấn & Tra Cứu Điện Ảnh Cho Cụm Rạp CGV Cinemas**, ứng dụng các kỹ thuật Xử lý Ngôn ngữ Tự nhiên (NLP), Hệ gợi ý dựa trên nội dung (Content-Based Recommendation System), và Kiến trúc Hybrid AI kết hợp RAG (Retrieval-Augmented Generation) với mô hình ngôn ngữ lớn (Google Gemini LLM).

---

## 1. Giới Thiệu Đề Tài

Xem phim chiếu rạp là một nhu cầu giải trí rất phổ biến. Tuy nhiên, khách hàng thường gặp khó khăn trong việc:
- Lựa chọn bộ phim phù hợp với tâm trạng, sở thích, hoặc độ tuổi người đi cùng (người yêu, trẻ em, gia đình).
- Tra cứu nhanh suất chiếu tại rạp gần nhất, tìm phòng chiếu định dạng đặc biệt (IMAX Laser, 4DX, Gold Class, Sweetbox).
- Nắm bắt bảng giá vé học sinh sinh viên U22, ưu đãi "Thứ Tư Vui Vẻ", hoặc chọn combo bắp nước tiết kiệm.

Dự án này xây dựng trợ lý ảo điện ảnh **Cimi** có khả năng giao tiếp tự nhiên bằng tiếng Việt, phân tích ngữ nghĩa câu hỏi, trích xuất thực thể, tính toán độ tương đồng để gợi ý phim chuẩn xác và mô phỏng toàn bộ quy trình chọn rạp, chọn ghế và xuất vé điện tử E-Ticket.

---

## 2. Các Kỹ Thuật Trí Tuệ Nhân Tạo (AI / NLP) Áp Dụng

### 2.1. Phân Loại Ý Định (Intent Classification)
- Nhận diện 8 nhóm ý định chính:
  1. `GREETING`: Chào hỏi, cảm ơn, hỏi thăm.
  2. `RECOMMEND_MOVIE`: Yêu cầu tư vấn / gợi ý phim theo cảm xúc, thể loại, đối tượng.
  3. `ASK_SHOWTIME`: Hỏi lịch chiếu, khung giờ chiếu tại rạp hoặc theo phim.
  4. `ASK_CINEMA`: Tra cứu địa chỉ, hotline, cụm rạp CGV theo tỉnh thành.
  5. `ASK_PRICE_PROMOTION`: Hỏi giá vé, chính sách vé U22, Thứ Tư Vui Vẻ, Ngày Văn Hóa.
  6. `ASK_COMBO`: Tra cứu menu bắp rang bơ, vị caramel/phô mai, combo nước ngọt.
  7. `MOVIE_DETAILS`: Hỏi tóm tắt nội dung phim, giới hạn độ tuổi (P, K, T13, T16, T18), đạo diễn, diễn viên, trailer.
  8. `BOOK_TICKET`: Yêu cầu đặt vé xem phim và giữ chỗ.
- Áp dụng kỹ thuật tính điểm trọng số theo mẫu câu ngữ nghĩa (Pattern Weight Scoring) kết hợp với ranh giới từ (Word Boundary Regex `\b`) giúp loại bỏ hoàn toàn hiện tượng nhận diện sai do trùng chuỗi con.

### 2.2. Trích Xuất Thực Thể (Named Entity Recognition - NER)
- Trích xuất tự động 7 nhóm thực thể trong hội thoại:
  - **Tên phim (`movie`)**: So khớp qua tên gốc, tên tiếng Việt và các bí danh/từ khóa độc quyền (Deadpool, Conan, Exhuma, Dune, Gru Minion, Godzilla...).
  - **Rạp CGV (`cinema`)**: Tự động nhận diện rạp dựa trên địa danh (Landmark 81, Bà Triệu, Sư Vạn Hạnh, Liễu Giai Metropolis, Aeon Mall Hà Đông...).
  - **Thể loại (`genres`)**: Hành động, Kinh dị, Hoạt hình, Hài hước, Tình cảm, Khoa học viễn tưởng, Tâm lý...
  - **Khung thời gian (`time`)**: Hôm nay, tối nay, ngày mai, cuối tuần.
  - **Định dạng (`formats`)**: 2D, 3D, IMAX Laser, 4DX, Gold Class, Sweetbox.
  - **Đối tượng đi cùng (`audience`)**: Trẻ em, gia đình, cặp đôi / người yêu, bạn bè, đi một mình.
  - **Thành phố (`city`)**: Hà Nội, TP. Hồ Chí Minh, Đà Nẵng.

### 2.3. Hệ Thống Gợi Ý Phim Dựa Trên Nội Dung (Content-Based Recommendation)
- **Mô hình Vector Không Gian (Vector Space Model)**:
  - Mỗi bộ phim được mô hình hóa thành một văn bản tổng hợp: `Tựa đề + Thể loại + Tóm tắt cốt truyện + Tags + Đạo diễn + Diễn viên + Định dạng`.
  - Trích xuất đặc trưng văn bản bằng giải thuật **TF-IDF (Term Frequency - Inverse Document Frequency)**.
- **Hàm Tương Đồng Cosine (Cosine Similarity)**:
  $$\text{Cosine Similarity}(Q, D) = \frac{\vec{Q} \cdot \vec{D}}{\|\vec{Q}\| \times \|\vec{D}\|}$$
- **Bộ Lọc Ràng Buộc & Trọng Số Kết Hợp (Constraint & Ranking Engine)**:
  - Ràng buộc cứng: Nếu người dùng đi cùng *trẻ em*, hệ thống tự động loại trừ các phim nhãn `T16`, `T18` và ưu tiên phim `P` (mọi lứa tuổi) hoặc `K`.
  - Kết hợp điểm chất lượng phim (Rating IMDb/CGV) và điểm ưu tiên phim đang chiếu rạp.
  - Tự động sinh ra lý do gợi ý thuyết phục người dùng (ví dụ: *"Thuộc thể loại bạn thích: Hài hước • Điểm đánh giá cực cao 8.9/10"*).

### 2.4. Kiến Trúc Hybrid AI & Kỹ Thuật RAG (Retrieval-Augmented Generation)
- **Chế độ Ngoại Tuyến (Local AI Engine)**: Chạy hoàn toàn độc lập với hiệu năng cao, độ trễ 0ms, không phụ thuộc vào internet hay API key bên ngoài.
- **Chế độ Đám Mây (Google Gemini LLM + RAG)**:
  - Khi người dùng cấu hình Gemini API Key, hệ thống tự động kích hoạt pipeline RAG.
  - RAG trích xuất các dữ kiện thực tế từ cơ sở dữ liệu CGV (phim, suất chiếu, giá vé) để đưa vào Context prompt, ngăn chặn tình trạng ảo giác (Hallucination) của LLM.

### 2.5. Tự Động Cập Nhật Phim Mới Mỗi Ngày (Automated CGV Crawler & Daily Scheduler)
- **Vượt rào cản chống bot F5 BIG-IP ASM**:
  - Trang CGV Việt Nam áp dụng cơ chế xác thực PoW (Proof-of-Work) bằng JavaScript `challenge()`.
  - Hệ thống tích hợp module Node.js siêu tốc giải mã CRC32 và tự động gửi response để lấy cookie phiên thực tế.
- **Bộ lập lịch chạy ngầm 24h (Daily Scheduler Background Task)**:
  - Tự động kích hoạt chu kỳ cập nhật dữ liệu phim mới sau mỗi 24 giờ kể từ khi máy chủ khởi chạy.
  - Tự động sinh suất chiếu tại các rạp CGV lớn và nạp lại (Hot-reload) bộ nhớ AI Engine (Entity Extractor, Recommender TF-IDF, RAG Pipeline) mà không làm gián đoạn máy chủ.
- **Đồng bộ chủ động qua Web UI & REST API**:
  - Cung cấp nút **"Đồng bộ CGV"** và badge hiển thị thời gian cập nhật ngay trên giao diện Web.
  - Hỗ trợ REST API `POST /api/movies/sync-cgv` và `GET /api/movies/sync-status`.

---

## 3. Cấu Trúc Dự Án

```
d:/BTL_TTNT/
│
├── data/                         # Cơ sở dữ liệu JSON của CGV
│   ├── movies.json               # 12+ bộ phim hot với đầy đủ metadata
│   ├── cinemas.json              # Hệ thống cụm rạp CGV toàn quốc
│   ├── showtimes.json            # Lịch chiếu chi tiết theo ngày và phòng chiếu
│   └── prices_combos.json        # Bảng giá vé, ưu đãi U22 và combo bắp nước
│
├── ai_engine/                    # Bộ lõi Xử lý Trí tuệ Nhân tạo
│   ├── __init__.py
│   ├── entity_extractor.py       # Module trích xuất thực thể (NER)
│   ├── intent_classifier.py      # Module phân loại ý định (Intent Classifier)
│   ├── recommender.py            # Thuật toán gợi ý Content-based (TF-IDF & Cosine)
│   ├── rag_pipeline.py           # Module truy xuất dữ kiện ngữ cảnh (RAG)
│   └── gemini_llm.py             # Tích hợp Google Gemini API & Local Generator
│
├── backend/                      # Máy chủ API (FastAPI)
│   ├── __init__.py
│   ├── app.py                   # Routing REST API, Daily Scheduler & phục vụ Static Files
│   ├── cgv_crawler.py           # Module cào & đồng bộ dữ liệu phim tự động từ CGV
│   ├── f5_solver.js             # Bộ giải thuật toán chống bot F5 BIG-IP ASM
│   └── models.py                 # Pydantic Schemas
│
├── frontend/                     # Giao diện Web CGV Cinema
│   ├── index.html                # Cấu trúc trang Web Single Page
│   ├── style.css                 # Giao diện Dark Cinema sang trọng chuẩn CGV
│   └── app.js                    # Xử lý tương tác, Voice input, sơ đồ ghế, vé
│
├── chay_bot.bat                  # File thực thi 1-click cho Windows
├── run_server.py                 # Script chạy server Python Uvicorn
├── test_nlp.py                   # Bộ kịch bản kiểm thử độ chính xác NLP/AI
├── requirements.txt              # Danh sách thư viện Python
└── README.md                     # Tài liệu hướng dẫn & báo cáo BTL
```

---

## 4. Hướng Dẫn Cài Đặt & Khởi Chạy

### Cách 1: Chạy nhanh bằng file Batch (Khuyên dùng trên Windows)
Chỉ cần nhấp đúp chuột vào file:
```cmd
chay_bot.bat
```
File sẽ tự động cài đặt thư viện cần thiết, khởi chạy server và tự động mở trình duyệt tại `http://localhost:8000`.

### Cách 2: Khởi chạy thủ công bằng dòng lệnh (Terminal / PowerShell)
1. Cài đặt các thư viện phụ thuộc:
```bash
python -m pip install -r requirements.txt
```

2. Khởi chạy máy chủ FastAPI:
```bash
python run_server.py
```

3. Mở trình duyệt Web và truy cập:
- **Giao diện Chatbot CGV**: `http://localhost:8000`
- **Tài liệu API Swagger UI**: `http://localhost:8000/docs`

---

## 5. Hướng Dẫn Kiểm Thử (Verification & Testing)

Để kiểm tra độ chính xác của các thuật toán AI/NLP độc lập, chạy lệnh:
```bash
python test_nlp.py
```

### Một số kịch bản câu hỏi mẫu để thử nghiệm trên Web:
1. **Gợi ý phim theo tâm trạng / thể loại**:
   - *"Tôi đang buồn quá, hãy gợi ý cho tôi 1 phim hài hước giải trí nhẹ nhàng"*
   - *"Cuối tuần này có phim kinh dị nào hay không?"*
2. **Gợi ý theo đối tượng đi cùng**:
   - *"Có phim hoạt hình nào bé 7 tuổi xem được không?"*
   - *"Gợi ý phim lãng mạn thích hợp đi xem cùng người yêu"*
3. **Tra cứu suất chiếu & rạp**:
   - *"Tối nay có phim Deadpool ở CGV Landmark 81 lúc mấy giờ?"*
   - *"Ở Hà Nội có những rạp CGV nào?"*
4. **Hỏi giá vé & combo**:
   - *"Giá vé học sinh sinh viên U22 và thứ 4 vui vẻ là bao nhiêu?"*
   - *"Combo bắp nước 2 người gồm những gì và giá thế nào?"*
5. **Xem chi tiết phim & đặt vé**:
   - *"Nội dung và diễn viên phim Quật Mộ Trùng Ma Exhuma"*
   - *"Tôi muốn đặt vé xem Deadpool ở CGV Bà Triệu"*
   - Bấm trực tiếp nút **"Đặt vé"** trên thẻ phim để trải nghiệm sơ đồ chọn ghế (Thường, VIP, Sweetbox) và nhận vé điện tử E-Ticket!
