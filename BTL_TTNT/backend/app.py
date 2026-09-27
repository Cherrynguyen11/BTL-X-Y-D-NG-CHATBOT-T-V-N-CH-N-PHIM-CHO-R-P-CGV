import os
import json
import random
import string
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import asyncio
from ai_engine.entity_extractor import EntityExtractor
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.recommender import MovieRecommender
from ai_engine.rag_pipeline import RAGPipeline
from ai_engine.gemini_llm import LLMService
from backend.models import ChatRequest, ChatResponse, RecommendRequest, KeyConfigRequest, BookingRequest
from backend.cgv_crawler import sync_cgv_movies, SYNC_STATUS_FILE

app = FastAPI(
    title="CGV AI Movie Assistant API",
    description="Hệ thống Chatbot AI tư vấn và tra cứu suất chiếu rạp CGV Cinemas (BTL TTNT)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Data containers
movies_data = []
cinemas_data = []
showtimes_data = []
prices_combos_data = []

extractor = None
classifier = None
recommender = None
rag = None
llm_service = LLMService()

def reload_all_data():
    """Nạp lại toàn bộ dữ liệu phim, rạp, lịch chiếu và khởi tạo lại bộ não AI"""
    global movies_data, cinemas_data, showtimes_data, prices_combos_data
    global extractor, classifier, recommender, rag

    with open(os.path.join(DATA_DIR, "movies.json"), encoding="utf-8") as f:
        movies_data = json.load(f)
    with open(os.path.join(DATA_DIR, "cinemas.json"), encoding="utf-8") as f:
        cinemas_data = json.load(f)
    with open(os.path.join(DATA_DIR, "showtimes.json"), encoding="utf-8") as f:
        showtimes_data = json.load(f)
    with open(os.path.join(DATA_DIR, "prices_combos.json"), encoding="utf-8") as f:
        prices_combos_data = json.load(f)

    extractor = EntityExtractor(movies_data, cinemas_data)
    classifier = IntentClassifier()
    recommender = MovieRecommender(movies_data)
    rag = RAGPipeline(movies_data, cinemas_data, showtimes_data, prices_combos_data)
    print(f"[AI Brain] Đã nạp thành công {len(movies_data)} phim, {len(cinemas_data)} rạp, {len(showtimes_data)} suất chiếu.")

# Khởi tạo dữ liệu lần đầu
reload_all_data()

async def daily_cgv_sync_worker():
    """Tác vụ chạy nền tự động đồng bộ phim mới từ CGV mỗi ngày"""
    # Đợi 5 giây sau khi server khởi động
    await asyncio.sleep(5)
    while True:
        try:
            print("[Daily Scheduler] Bắt đầu kiểm tra cập nhật phim mới từ CGV...")
            result = sync_cgv_movies(force=False)
            if result.get("new_movies_added", 0) > 0:
                reload_all_data()
                print(f"[Daily Scheduler] Đã nạp thêm {result['new_movies_added']} phim mới từ CGV vào AI.")
            else:
                print(f"[Daily Scheduler] CGV đã đồng bộ trước đó. {result.get('message', '')}")
        except Exception as err:
            print(f"[Daily Scheduler] Lỗi khi tự động đồng bộ CGV: {err}")
        
        # Chờ 24 tiếng (86400 giây) trước lần quét tiếp theo
        await asyncio.sleep(86400)

@app.on_event("startup")
async def on_startup():
    # Kích hoạt worker tự động cập nhật phim mỗi ngày
    asyncio.create_task(daily_cgv_sync_worker())

# Quick reply suggestions mapping
QUICK_REPLIES_BY_INTENT = {
    "GREETING": ["🔥 Phim đang hot hôm nay", "🍿 Xem combo bắp nước", "🎟️ Giá vé học sinh U22", "🎭 Gợi ý phim kinh dị"],
    "RECOMMEND_MOVIE": ["🎬 Đặt vé phim này", "🕒 Xem suất chiếu", "🎥 Xem Trailer", "✨ Gợi ý phim khác"],
    "ASK_SHOWTIME": ["🎟️ Chọn ghế & Đặt vé", "📍 Xem địa chỉ rạp", "🍿 Mua kèm combo bắp", "📅 Lịch ngày mai"],
    "ASK_CINEMA": ["🕒 Xem suất chiếu tại rạp này", "🚗 Hướng dẫn gửi xe", "🍿 Combo ưu đãi"],
    "ASK_PRICE_PROMOTION": ["🎓 Đăng ký thẻ U22", "🎉 Thứ 4 vui vẻ", "🍿 Xem giá bắp nước", "🎬 Xem phim đang chiếu"],
    "ASK_COMBO": ["🍿 Đặt kèm bắp khi mua vé", "🥤 Combo 2 người", "🎟️ Xem bảng giá vé"],
    "MOVIE_DETAILS": ["🕒 Xem suất chiếu", "🎟️ Đặt vé ngay", "🎥 Xem Trailer", "⭐ Phim tương tự"],
    "BOOK_TICKET": ["🕒 Chọn suất chiếu", "💺 Mở sơ đồ chọn ghế", "📍 Đổi cụm rạp khác"],
    "GENERAL_QA": ["🎟️ Giá vé CGV", "🍿 Combo bắp nước", "🔥 Phim đang chiếu"]
}

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Tin nhắn không được để trống")

    # Nếu người dùng truyền API Key từ client
    if req.gemini_key:
        llm_service.set_api_key(req.gemini_key)

    # 1. Trích xuất thực thể (NER)
    entities = extractor.extract_all(user_msg)
    
    # 2. Phân loại ý định (Intent Classification)
    intent, confidence = classifier.classify(user_msg, entities)
    
    # 3. Gợi ý phim qua TF-IDF & Cosine Similarity
    suggested_movies_data = []
    if intent in ["RECOMMEND_MOVIE", "GREETING"] or (not entities["movie"] and entities["genres"]):
        rec_results = recommender.recommend(user_msg, entities, top_k=3)
        for r in rec_results:
            m = dict(r["movie"])
            m["ai_reason"] = r["reason"]
            m["match_score"] = r["score"]
            suggested_movies_data.append(m)
    elif entities["movie"]:
        suggested_movies_data.append(entities["movie"])

    # 4. Truy xuất suất chiếu liên quan
    showtimes_list = []
    if entities["movie"]:
        for st in showtimes_data:
            if st["movie_id"] == entities["movie"]["id"]:
                c = next((cin for cin in cinemas_data if cin["id"] == st["cinema_id"]), None)
                showtimes_list.append({
                    "cinema_name": c["name"] if c else st["cinema_id"],
                    "cinema_id": st["cinema_id"],
                    "movie_title": entities["movie"]["title"],
                    "movie_id": entities["movie"]["id"],
                    "screen": st["screen"],
                    "format": st["format"],
                    "times": st["times"]
                })
    elif entities["cinema"]:
        for st in showtimes_data:
            if st["cinema_id"] == entities["cinema"]["id"]:
                m = next((mov for mov in movies_data if mov["id"] == st["movie_id"]), None)
                if m:
                    showtimes_list.append({
                        "cinema_name": entities["cinema"]["name"],
                        "cinema_id": entities["cinema"]["id"],
                        "movie_title": m["title"],
                        "movie_id": m["id"],
                        "screen": st["screen"],
                        "format": st["format"],
                        "times": st["times"]
                    })

    # 5. RAG: Truy xuất ngữ cảnh
    context_data = rag.retrieve_context(intent, entities)
    context_str = rag.format_context_for_llm(context_data)

    # 6. Sinh câu trả lời (Gemini RAG hoặc Local Rule-based Generator)
    engine_mode = "Gemini LLM (RAG)" if llm_service.api_key else "Local AI Engine"
    reply = llm_service.generate_response(
        user_message=user_msg,
        intent=intent,
        entities=entities,
        context_str=context_str,
        rec_movies=[{"movie": m, "reason": m.get("ai_reason", "")} for m in suggested_movies_data] if suggested_movies_data else None
    )

    # Tạo Entity Summary sạch cho Frontend debug
    entities_clean = {
        "movie": entities["movie"]["title"] if entities["movie"] else None,
        "cinema": entities["cinema"]["name"] if entities["cinema"] else None,
        "genres": entities["genres"],
        "formats": entities["formats"],
        "city": entities["city"],
        "time": entities["time"],
        "audience": entities["audience"]
    }

    quick_replies = QUICK_REPLIES_BY_INTENT.get(intent, ["🔥 Phim hot", "🕒 Lịch chiếu", "🍿 Bắp nước", "🎟️ Giá vé"])

    return ChatResponse(
        reply=reply,
        intent=intent,
        confidence=round(confidence, 2),
        entities=entities_clean,
        suggested_movies=suggested_movies_data,
        showtimes=showtimes_list,
        quick_replies=quick_replies,
        engine_mode=engine_mode
    )

@app.get("/api/movies")
def get_movies(status: str = None):
    if status:
        return [m for m in movies_data if m.get("status") == status]
    return movies_data

@app.get("/api/cinemas")
def get_cinemas(city: str = None):
    if city:
        return [c for c in cinemas_data if city.lower() in c.get("city", "").lower()]
    return cinemas_data

@app.get("/api/showtimes")
def get_showtimes(movie_id: str = None, cinema_id: str = None):
    results = []
    for st in showtimes_data:
        if movie_id and st["movie_id"] != movie_id:
            continue
        if cinema_id and st["cinema_id"] != cinema_id:
            continue
        
        m = next((mov for mov in movies_data if mov["id"] == st["movie_id"]), None)
        c = next((cin for cin in cinemas_data if cin["id"] == st["cinema_id"]), None)
        results.append({
            "movie": m,
            "cinema": c,
            "screen": st["screen"],
            "format": st["format"],
            "times": st["times"]
        })
    return results

@app.get("/api/prices")
def get_prices():
    return prices_combos_data

@app.get("/api/movies/reload")
def reload_movies_endpoint():
    """Tải lại dữ liệu phim từ file movies.json vào bộ nhớ AI"""
    reload_all_data()
    return {"status": "success", "total_movies": len(movies_data), "message": "Đã nạp lại toàn bộ dữ liệu phim mới nhất!"}

@app.post("/api/movies/sync-cgv")
def sync_cgv_endpoint(force: bool = True):
    """Kích hoạt cào và đồng bộ phim mới từ CGV Việt Nam"""
    try:
        res = sync_cgv_movies(force=force)
        reload_all_data()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đồng bộ CGV: {str(e)}")

@app.get("/api/movies/sync-status")
def get_sync_status():
    """Lấy trạng thái và thời gian đồng bộ CGV lần gần nhất"""
    if os.path.exists(SYNC_STATUS_FILE):
        try:
            with open(SYNC_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "status": "idle",
        "last_sync": "Chưa có thông tin",
        "total_movies": len(movies_data),
        "new_movies_added": 0,
        "message": "Chưa thực hiện đồng bộ"
    }

@app.post("/api/config/key")
def set_api_key(req: KeyConfigRequest):
    llm_service.set_api_key(req.api_key)
    return {"status": "success", "mode": "Gemini LLM (RAG)" if req.api_key else "Local AI Engine"}

@app.get("/api/config/status")
def get_status():
    sync_info = get_sync_status()
    return {
        "engine": "Gemini LLM (RAG)" if llm_service.api_key else "Local AI Engine",
        "has_gemini_key": bool(llm_service.api_key),
        "total_movies": len(movies_data),
        "total_cinemas": len(cinemas_data),
        "total_showtimes": len(showtimes_data),
        "last_sync": sync_info.get("last_sync", "Chưa có thông tin"),
        "sync_status": sync_info.get("status", "idle")
    }

@app.post("/api/book-seat")
def book_seat(req: BookingRequest):
    """Giả lập đặt vé & tạo mã vé CGV điện tử"""
    m = next((mov for mov in movies_data if mov["id"] == req.movie_id), None)
    c = next((cin for cin in cinemas_data if cin["id"] == req.cinema_id), None)
    
    if not m or not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin phim hoặc rạp")

    ticket_code = "CGV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Tính tiền vé giả lập
    price_per_seat = 110000 if req.format == "2D" else (180000 if req.format == "IMAX" else 150000)
    total_price = price_per_seat * len(req.seats)
    
    return {
        "status": "confirmed",
        "ticket_code": ticket_code,
        "movie_title": m["title"],
        "poster": m["poster"],
        "age_rating": m["age_rating"],
        "cinema_name": c["name"],
        "address": c["address"],
        "showtime": req.showtime,
        "format": req.format,
        "seats": req.seats,
        "total_price": f"{total_price:,.0f} VNĐ",
        "booking_time": "Hôm nay",
        "message": "Đặt vé thành công! Vui lòng đưa mã vé này tại quầy vé hoặc máy lấy vé tự động của CGV."
    }

# Phục vụ giao diện Web Frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "CGV AI Chatbot Backend is Running. Frontend not yet initialized."}
