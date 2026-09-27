import json
import os
import sys

# Đảm bảo in UTF-8 trơn tru trên Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from ai_engine.entity_extractor import EntityExtractor
from ai_engine.intent_classifier import IntentClassifier
from ai_engine.recommender import MovieRecommender
from ai_engine.rag_pipeline import RAGPipeline

def run_tests():
    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, "data", "movies.json"), encoding="utf-8") as f:
        movies = json.load(f)
    with open(os.path.join(base_dir, "data", "cinemas.json"), encoding="utf-8") as f:
        cinemas = json.load(f)
    with open(os.path.join(base_dir, "data", "showtimes.json"), encoding="utf-8") as f:
        showtimes = json.load(f)
    with open(os.path.join(base_dir, "data", "prices_combos.json"), encoding="utf-8") as f:
        prices_combos = json.load(f)

    extractor = EntityExtractor(movies, cinemas)
    classifier = IntentClassifier()
    recommender = MovieRecommender(movies)
    rag = RAGPipeline(movies, cinemas, showtimes, prices_combos)

    test_queries = [
        "Xin chào bạn, hôm nay có phim gì hay không?",
        "Tối nay có phim kinh dị nào chiếu ở Landmark 81 không?",
        "Phim Doraemon và Kẻ Trộm Mặt Trăng có cho trẻ 6 tuổi xem không?",
        "Giá vé học sinh sinh viên U22 và thứ 4 vui vẻ là bao nhiêu?",
        "Combo bắp nước 2 người giá bao nhiêu tiền?",
        "Tôi muốn đặt vé xem Deadpool ở CGV Bà Triệu",
        "Tôi đang buồn quá, hãy gợi ý cho tôi 1 phim hài hước giải trí nhẹ nhàng",
        "Nội dung và diễn viên phim Quật Mộ Trùng Ma Exhuma",
        "Ở Hà Nội có những rạp CGV nào?"
    ]

    print("=" * 60)
    print("KIỂM THỬ BỘ LÕI AI & NLP CHO CHATBOT CGV (BTL TTNT)")
    print("=" * 60)

    for i, q in enumerate(test_queries, 1):
        entities = extractor.extract_all(q)
        intent, conf = classifier.classify(q, entities)
        recs = recommender.recommend(q, entities, top_k=2)

        print(f"\n[Test {i}]: '{q}'")
        print(f" -> Intent: {intent} (Độ tin cậy: {conf:.2f})")
        
        extracted_info = []
        if entities['movie']: extracted_info.append(f"Phim: {entities['movie']['title']}")
        if entities['cinema']: extracted_info.append(f"Rạp: {entities['cinema']['name']}")
        if entities['genres']: extracted_info.append(f"Thể loại: {', '.join(entities['genres'])}")
        if entities['audience']: extracted_info.append(f"Đối tượng: {entities['audience']}")
        if entities['time']: extracted_info.append(f"Thời gian: {entities['time']}")
        print(f" -> Thực thể (NER): {', '.join(extracted_info) if extracted_info else 'Không có'}")
        
        if intent == "RECOMMEND_MOVIE" and recs:
            top_m = recs[0]["movie"]
            print(f" -> Gợi ý AI (TF-IDF Cosine): {top_m['title']} ({top_m['rating']}⭐) - Lý do: {recs[0]['reason']}")

    print("\n" + "=" * 60)
    print("TẤT CẢ CÁC BỘ TEST AI/NLP HOÀN THÀNH XUẤT SẮC!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
