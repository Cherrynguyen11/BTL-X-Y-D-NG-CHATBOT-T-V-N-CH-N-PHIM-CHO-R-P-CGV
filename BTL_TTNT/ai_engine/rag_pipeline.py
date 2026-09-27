class RAGPipeline:
    """
    Retrieval-Augmented Generation (RAG) Pipeline:
    Truy xuất thông tin chính xác từ cơ sở dữ liệu CGV và xây dựng ngữ cảnh (Context)
    để cấp cho LLM (hoặc Local Generator) trả lời không bịa đặt.
    """

    def __init__(self, movies: list, cinemas: list, showtimes: list, prices_combos: dict):
        self.movies = movies
        self.cinemas = cinemas
        self.showtimes = showtimes
        self.prices_combos = prices_combos
        
        # Tạo mapping để tra cứu nhanh
        self.movies_by_id = {m["id"]: m for m in movies}
        self.cinemas_by_id = {c["id"]: c for c in cinemas}

    def retrieve_context(self, intent: str, entities: dict) -> dict:
        context_data = {
            "relevant_movies": [],
            "relevant_showtimes": [],
            "relevant_cinemas": [],
            "pricing_info": None,
            "combos_info": None
        }
        
        # 1. Nếu có movie cụ thể
        movie = entities.get("movie")
        if movie:
            context_data["relevant_movies"].append(movie)
            # Tìm suất chiếu của phim này
            for st in self.showtimes:
                if st["movie_id"] == movie["id"]:
                    cinema = self.cinemas_by_id.get(st["cinema_id"])
                    context_data["relevant_showtimes"].append({
                        "cinema_name": cinema["name"] if cinema else st["cinema_id"],
                        "city": cinema.get("city") if cinema else "",
                        "screen": st.get("screen", ""),
                        "format": st.get("format", "2D"),
                        "times": st.get("times", [])
                    })

        # 2. Nếu có rạp cụ thể
        cinema = entities.get("cinema")
        if cinema:
            context_data["relevant_cinemas"].append(cinema)
            # Tìm tất cả phim đang chiếu ở rạp này
            for st in self.showtimes:
                if st["cinema_id"] == cinema["id"]:
                    m = self.movies_by_id.get(st["movie_id"])
                    if m and m not in context_data["relevant_movies"]:
                        context_data["relevant_movies"].append(m)

        # 3. Thông tin giá vé hoặc combo
        if intent in ["ASK_PRICE_PROMOTION", "GENERAL_QA"]:
            context_data["pricing_info"] = self.prices_combos.get("ticket_prices")
            context_data["promotions"] = self.prices_combos.get("promotions")

        if intent in ["ASK_COMBO", "GENERAL_QA"]:
            context_data["combos_info"] = self.prices_combos.get("combos")

        return context_data

    def format_context_for_llm(self, context_data: dict) -> str:
        """Định dạng context thành văn bản dễ hiểu cho LLM"""
        lines = []
        
        if context_data.get("relevant_movies"):
            lines.append("=== THÔNG TIN PHIM LIÊN QUAN ===")
            for m in context_data["relevant_movies"]:
                lines.append(
                    f"- Phim: {m['title']} ({m.get('original_title', '')})\n"
                    f"  Thể loại: {', '.join(m.get('genre', []))} | Thời lượng: {m.get('duration')} phút | Giới hạn tuổi: {m.get('age_rating')} ({m.get('age_desc')})\n"
                    f"  Đạo diễn: {m.get('director')} | Diễn viên: {', '.join(m.get('cast', []))}\n"
                    f"  Điểm đánh giá: {m.get('rating')}/10 | Định dạng: {', '.join(m.get('formats', []))}\n"
                    f"  Tóm tắt: {m.get('synopsis')}"
                )
                
        if context_data.get("relevant_showtimes"):
            lines.append("\n=== SUẤT CHIẾU TẠI CÁC RẠP CGV ===")
            for st in context_data["relevant_showtimes"]:
                lines.append(
                    f"- Rạp: {st['cinema_name']} ({st['city']}) | Phòng: {st['screen']} [{st['format']}]\n"
                    f"  Giờ chiếu: {', '.join(st['times'])}"
                )

        if context_data.get("relevant_cinemas"):
            lines.append("\n=== THÔNG TIN CỤM RẠP CGV ===")
            for c in context_data["relevant_cinemas"]:
                lines.append(
                    f"- {c['name']} | Địa chỉ: {c['address']} | TP: {c['city']} | Hotline: {c['phone']} | Định dạng: {', '.join(c['formats'])}"
                )

        if context_data.get("pricing_info"):
            lines.append("\n=== BẢNG GIÁ VÉ CGV ===")
            for k, v in context_data["pricing_info"].items():
                lines.append(f"- {v.get('name')}: {v}")

        if context_data.get("combos_info"):
            lines.append("\n=== BẮP NƯỚC & COMBO CGV ===")
            for cb in context_data["combos_info"]:
                lines.append(f"- {cb['name']}: {cb['price']} ({cb['desc']})")
                
        return "\n".join(lines)
