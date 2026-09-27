from .entity_extractor import remove_accents, word_boundary_search

class IntentClassifier:
    """
    Bộ phân loại ý định người dùng (Intent Classifier) cho Chatbot CGV.
    Sử dụng kết hợp trọng số từ khóa, mẫu câu (Pattern matching) và thực thể nhận diện.
    """
    
    INTENTS = {
        "GREETING": "Chào hỏi / Tạm biệt / Hỏi thăm",
        "RECOMMEND_MOVIE": "Yêu cầu gợi ý phim",
        "ASK_SHOWTIME": "Hỏi suất chiếu / Giờ chiếu",
        "ASK_CINEMA": "Hỏi thông tin địa chỉ rạp CGV",
        "ASK_PRICE_PROMOTION": "Hỏi giá vé / Khuyến mãi / Ưu đãi U22, thứ 4",
        "ASK_COMBO": "Hỏi bắp nước / Combo bắp nước / Bỏng ngô",
        "MOVIE_DETAILS": "Hỏi thông tin chi tiết phim (nội dung, độ tuổi, diễn viên, đạo diễn, trailer)",
        "BOOK_TICKET": "Muốn mua vé / Đặt vé",
        "GENERAL_QA": "Câu hỏi chung về rạp / Quy định CGV"
    }
    
    def __init__(self):
        self.intent_patterns = {
            "GREETING": [
                "xin chao", "chao ban", "chao ad", "hello", "hi bot", "hi cimi",
                "tam biet", "bye", "cam on", "thanks", "chuc mot ngay tot lanh"
            ],
            "ASK_COMBO": [
                "bap", "bong ngo", "bap nuoc", "popcorn", "combo", "my combo",
                "sweet combo", "cgv combo", "do an", "nuoc ngot", "snack", "an vat",
                "khoai tay lac", "xuc xich"
            ],
            "ASK_PRICE_PROMOTION": [
                "gia ve", "bao nhieu tien", "ve bao nhieu", "u22", "hoc sinh", "sinh vien",
                "thu 4 vui ve", "happy wednesday", "khuyen mai", "giam gia", "uu dai",
                "gia imax", "gia 4dx", "gold class bao nhieu", "gia sweetbox",
                "thanh vien", "tich diem"
            ],
            "ASK_SHOWTIME": [
                "suat chieu", "lich chieu", "may gio", "gio chieu", "chieu luc nao",
                "chieu gio nao", "co chieu khong", "con suat nao", "gio nao co",
                "toi nay chieu gi", "hom nay chieu gi", "chieu o", "chieu tai"
            ],
            "ASK_CINEMA": [
                "rap o dau", "dia chi rap", "rap cgv o", "cgv gan day", "cgv tai",
                "so dien thoai rap", "rap nao", "co nhung rap", "rap cgv nao", "he thong rap"
            ],
            "BOOK_TICKET": [
                "dat ve", "mua ve", "lay ve", "book ve", "giu cho", "chon ghe",
                "huong dan dat ve", "link dat ve"
            ],
            "MOVIE_DETAILS": [
                "noi dung", "dien vien", "dao dien", "trailer", "bao nhieu phut",
                "thoi luong", "may tuoi", "do tuoi", "t18 la gi", "t16 la gi",
                "phim ke ve gi", "co hay khong", "review", "danh gia", "cho tre", "xem duoc khong"
            ],
            "RECOMMEND_MOVIE": [
                "goi y", "tu van", "nen xem", "phim gi hay", "phim nao hay", "phim hot",
                "dang hot", "xem gi", "dang chieu gi", "cuoi tuan nay xem gi", "di voi nguoi yeu",
                "cho tre em", "kinh di nao hay", "hai nao hay", "buon qua", "muon xem phim", "co phim gi"
            ],
            "GENERAL_QA": [
                "mang do an ngoai", "quy dinh", "duoc mang", "vao tre", "doi ve",
                "huy ve", "mat ve", "gui xe"
            ]
        }

    def classify(self, text: str, entities: dict) -> tuple[str, float]:
        norm = remove_accents(text)
        scores = {intent: 0.0 for intent in self.INTENTS}
        
        # 1. Khớp từ khóa & pattern với ranh giới từ
        for intent, patterns in self.intent_patterns.items():
            for p in patterns:
                if word_boundary_search(p, norm):
                    scores[intent] += 1.5 + (len(p.split()) * 0.8)
                    
        # 2. Xử lý logic theo thực thể & ngữ cảnh
        if entities.get("cinema") and any(w in norm for w in ["chieu", "suat", "gio", "toi nay", "hom nay"]):
            scores["ASK_SHOWTIME"] += 4.0

        if any(w in norm for w in ["rap nao", "co nhung rap", "dia chi"]) and (entities.get("city") or "cgv" in norm):
            scores["ASK_CINEMA"] += 5.0

        if any(w in norm for w in ["gia ve", "bao nhieu tien", "u22", "khuyen mai"]):
            scores["ASK_PRICE_PROMOTION"] += 4.0
            
        if any(w in norm for w in ["bap", "popcorn", "combo"]):
            scores["ASK_COMBO"] += 4.5

        if any(w in norm for w in ["dat ve", "mua ve", "book ve"]):
            scores["BOOK_TICKET"] += 4.5

        if any(w in norm for w in ["cho tre", "may tuoi", "do tuoi", "noi dung", "dien vien", "dao dien"]):
            scores["MOVIE_DETAILS"] += 4.0

        if any(w in norm for w in ["goi y", "tu van", "nen xem", "phim gi hay", "buon qua", "co phim gi"]):
            scores["RECOMMEND_MOVIE"] += 4.0

        # Nếu có thể loại mà không có rạp hay giờ chiếu -> gợi ý phim
        if entities.get("genres") and not entities.get("cinema") and scores["ASK_SHOWTIME"] < 3.0:
            scores["RECOMMEND_MOVIE"] += 3.0

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]
        
        if max_score == 0:
            if len(norm.split()) <= 2:
                return "GREETING", 0.6
            return "RECOMMEND_MOVIE", 0.5
            
        confidence = min(0.99, 0.55 + (max_score / 12.0))
        return best_intent, confidence
