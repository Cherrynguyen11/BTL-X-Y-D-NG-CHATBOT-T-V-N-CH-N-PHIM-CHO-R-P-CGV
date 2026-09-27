import requests
import json
import os

CGV_SYSTEM_PROMPT = """Bạn là Cimi - Trợ lý ảo AI thông minh, thân thiện và am hiểu điện ảnh của cụm rạp CGV Cinemas Việt Nam.
Phong cách trò chuyện:
- Lịch sự, niềm nở, trẻ trung, dùng ngôi xưng 'mình' hoặc 'Cimi' và gọi khách hàng là 'bạn'.
- Thường xuyên dùng các emoji liên quan đến rạp phim (🍿, 🎬, 🎟️, ⭐, 🥤, ❤️).
- Trả lời ngắn gọn, rành mạch, làm nổi bật thông tin quan trọng (tên phim, giờ chiếu, giá vé).
- Khi tư vấn phim, hãy nêu rõ độ tuổi quy định (P, K, T13, T16, T18) và lý do phim hấp dẫn.
- Tuyệt đối chỉ cung cấp thông tin dựa trên dữ liệu ngữ cảnh CGV được cung cấp dưới đây, không tự bịa đặt lịch chiếu hay thông tin rạp không có thật.
- Khuyến khích khách hàng chọn suất chiếu hoặc đặt vé xem phim tại rạp CGV.
"""

class LLMService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-1.5-flash"
        
    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    def generate_response(self, user_message: str, intent: str, entities: dict, context_str: str, rec_movies: list = None) -> str:
        """
        Sinh câu trả lời. Nếu có Gemini API Key thì gọi API Gemini với RAG context.
        Nếu không có hoặc lỗi mạng thì dùng Local Template Generator thông minh.
        """
        if self.api_key:
            try:
                response = self._call_gemini(user_message, context_str, rec_movies)
                if response:
                    return response
            except Exception as e:
                print(f"[Gemini API Warning] {e}, chuyển sang Local Generator...")

        # Fallback sang bộ sinh câu trả lời cục bộ
        return self._generate_local_response(user_message, intent, entities, rec_movies)

    def _call_gemini(self, user_message: str, context_str: str, rec_movies: list = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        prompt = f"""{CGV_SYSTEM_PROMPT}

DỮ LIỆU THỰC TẾ TỪ HỆ THỐNG RẠP CGV:
{context_str}

CÂU HỎI CỦA KHÁCH HÀNG:
"{user_message}"

Hãy trả lời khách hàng một cách tự nhiên, chu đáo và chuẩn xác nhất:"""

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800
            }
        }
        
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        else:
            print(f"Gemini API Error: {resp.status_code} - {resp.text}")
        return None

    def _generate_local_response(self, user_message: str, intent: str, entities: dict, rec_movies: list = None) -> str:
        """
        Bộ sinh câu trả lời thông minh dựa trên luật & slot-filling (Offline Rule-Based Generator)
        """
        movie = entities.get("movie")
        cinema = entities.get("cinema")
        genres = entities.get("genres", [])
        time_period = entities.get("time")
        audience = entities.get("audience")
        
        if intent == "GREETING":
            return (
                "🍿 **Xin chào bạn! Cimi là trợ lý ảo của CGV Cinemas.** 🎬\n\n"
                "Hôm nay bạn muốn xem phim gì nào? Cimi có thể giúp bạn:\n"
                "• Gợi ý phim hot theo sở thích, tâm trạng hoặc lứa tuổi\n"
                "• Tra cứu lịch chiếu và phòng vé các rạp CGV toàn quốc\n"
                "• Xem bảng giá vé, ưu đãi U22, thứ 4 vui vẻ & combo bắp nước 🥤\n\n"
                "Bạn có thể nhắn ngay câu hỏi hoặc chọn các gợi ý bên dưới nhé!"
            )

        if intent == "RECOMMEND_MOVIE":
            if rec_movies:
                top_m = rec_movies[0]["movie"]
                resp = f"🎬 **Cimi xin gợi ý cho bạn siêu phẩm: {top_m['title']}** ({top_m.get('rating')}/10 ⭐)\n\n"
                resp += f"• **Thể loại**: {', '.join(top_m.get('genre', []))}\n"
                resp += f"• **Thời lượng**: {top_m.get('duration')} phút | **Độ tuổi**: {top_m.get('age_rating')} ({top_m.get('age_desc')})\n"
                resp += f"• **Lý do nên xem**: {rec_movies[0].get('reason')}\n\n"
                resp += f"_{top_m.get('synopsis')}_\n\n"
                if len(rec_movies) > 1:
                    resp += "Ngoài ra, bạn cũng có thể tham khảo thêm các phim tương tự ở danh sách bên dưới nhé! 👇"
                return resp
            return "Hiện tại CGV đang có rất nhiều phim hấp dẫn! Bạn hãy cho Cimi biết thể loại bạn thích (hành động, hoạt hình, kinh dị...) để Cimi tư vấn chuẩn nhất nhé!"

        if intent == "ASK_SHOWTIME":
            if movie and cinema:
                return (
                    f"🎟️ **Lịch chiếu phim {movie['title']} tại {cinema['name']}:**\n\n"
                    f"• **Hôm nay**: Các suất chiếu linh hoạt từ sáng đến tối muộn.\n"
                    f"• **Định dạng hỗ trợ**: {', '.join(movie.get('formats', ['2D']))}\n\n"
                    f"Bạn hãy bấm vào nút **'Xem suất chiếu'** trên thẻ phim bên dưới để chọn giờ và đặt ghế ngay nhé!"
                )
            elif movie:
                return (
                    f"🎟️ Phim **{movie['title']}** hiện đang có suất chiếu tại các cụm rạp CGV (Hà Nội, TP.HCM, Đà Nẵng) với các định dạng {', '.join(movie.get('formats', []))}!\n\n"
                    f"Bạn muốn xem ở cụm rạp nào (ví dụ: Vincom Bà Triệu, Landmark 81, Sư Vạn Hạnh...)? Cimi sẽ tra ngay lịch chiếu chi tiết cho bạn!"
                )
            elif cinema:
                return (
                    f"🍿 **Tại {cinema['name']}** hôm nay đang có lịch chiếu các phim cực hot như: Deadpool & Wolverine, Những Mảnh Ghép Cảm Xúc 2, Ma Da, Exhuma...\n\n"
                    f"Địa chỉ rạp: {cinema.get('address')} (Hotline: {cinema.get('phone')}). Bạn muốn tra cứu lịch của phim nào tại rạp này ạ?"
                )
            return "Bạn muốn xem suất chiếu của bộ phim nào và tại cụm rạp CGV khu vực nào ạ? Hãy nhắn cho Cimi (ví dụ: *'Suất chiếu Deadpool tối nay ở Landmark 81'*) nhé!"

        if intent == "MOVIE_DETAILS":
            if movie:
                return (
                    f"🎬 **THÔNG TIN CHI TIẾT PHIM: {movie['title'].upper()}**\n"
                    f"• **Tựa gốc**: {movie.get('original_title')}\n"
                    f"• **Điểm đánh giá**: ⭐ {movie.get('rating')}/10 ({movie.get('votes', 0):,} lượt vote)\n"
                    f"• **Thể loại**: {', '.join(movie.get('genre', []))}\n"
                    f"• **Thời lượng**: {movie.get('duration')} phút\n"
                    f"• **Quy định độ tuổi**: **{movie.get('age_rating')}** - {movie.get('age_desc')}\n"
                    f"• **Đạo diễn**: {movie.get('director')}\n"
                    f"• **Diễn viên**: {', '.join(movie.get('cast', []))}\n"
                    f"• **Định dạng**: {', '.join(movie.get('formats', []))}\n\n"
                    f"📖 **Nội dung tóm tắt**: {movie.get('synopsis')}\n\n"
                    f"Bạn có thể bấm vào thẻ phim bên dưới để **Xem Trailer** hoặc **Đặt vé** ngay nhé!"
                )
            return "Bạn muốn tìm hiểu chi tiết về bộ phim nào ạ? Cimi có đầy đủ thông tin về nội dung, diễn viên, thời lượng và giới hạn độ tuổi đó!"

        if intent == "ASK_PRICE_PROMOTION":
            return (
                "🎟️ **BẢNG GIÁ VÉ & ƯU ĐÃI NỔI BẬT TẠI CGV CINEMAS:**\n\n"
                "1. **Vé 2D Tiêu Chuẩn**:\n"
                "   • Khách hàng U22 / HSSV: từ **55.000đ - 75.000đ** (Thứ 2 - Thứ 6)\n"
                "   • Người lớn (Thứ 2 - Thứ 5): **85.000đ - 110.000đ**\n"
                "   • Cuối tuần (T6, T7, CN): **110.000đ - 135.000đ**\n"
                "2. **Định dạng đặc biệt**:\n"
                "   • **IMAX Laser**: 150.000đ - 230.000đ\n"
                "   • **4DX (Ghế rung & hiệu ứng)**: 140.000đ - 210.000đ\n"
                "   • **Gold Class VIP**: 300.000đ/vé (kèm trà/cà phê và phòng chờ VIP)\n"
                "3. **Ưu đãi cực hot**:\n"
                "   • 🎉 **Thứ Tư Vui Vẻ (Happy Wednesday)**: Đồng giá chỉ từ **75.000đ**\n"
                "   • 🎓 **U22 Member**: Giá vé ưu đãi không giới hạn số lần cho thành viên dưới 22 tuổi\n"
                "   • 🌟 **Culture Day**: Đồng giá **55.000đ** vào thứ Hai cuối cùng mỗi tháng!"
            )

        if intent == "ASK_COMBO":
            return (
                "🍿 **THỰC ĐƠN BẮP NƯỚC & COMBO CGV ĐƯỢC YÊU THÍCH NHẤT:**\n\n"
                "• **My Combo (1 người)**: 1 Bắp ngọt lớn + 1 Nước lớn 👉 **89.000đ**\n"
                "• **CGV Combo (Bán chạy nhất - 2 người)**: 1 Bắp 2 ngăn (chọn vị Caramel / Phô mai) + 2 Nước lớn 👉 **119.000đ**\n"
                "• **Sweet Combo (Cặp đôi lãng mạn)**: 1 Bắp lớn + 2 Nước + 1 Snack giòn ngọt ngào 👉 **135.000đ**\n"
                "• **Family Combo (Gia đình)**: 2 Bắp đặc biệt + 4 Nước + Xúc xích nướng / Khoai tây lắc 👉 **219.000đ**\n\n"
                "✨ *Mẹo nhỏ*: Bạn có thể đổi vị Phô mai lắc hoặc Caramel đậm đà chỉ thêm 10.000đ thôi nhé!"
            )

        if intent == "ASK_CINEMA":
            return (
                "📍 **HỆ THỐNG CỤM RẠP CGV HIỆN ĐẠI TOÀN QUỐC:**\n\n"
                "🏛️ **Khu vực Hà Nội**:\n"
                "• CGV Vincom Bà Triệu (Tầng 6, 191 Bà Triệu)\n"
                "• CGV Metropolis Liễu Giai (Tầng M3, 29 Liễu Giai - Phòng IMAX)\n"
                "• CGV Aeon Mall Hà Đông (Tầng 3 - Phòng IMAX & 4DX)\n"
                "• CGV Tràng Tiền Plaza (Tầng 5, 24 Hai Bà Trưng)\n\n"
                "🏙️ **Khu vực TP. Hồ Chí Minh**:\n"
                "• CGV Landmark 81 (Tầng B1, Tòa Landmark 81 - Phòng IMAX Laser)\n"
                "• CGV Sư Vạn Hạnh (Tầng 6 Vạn Hạnh Mall - Phòng 4DX)\n"
                "• CGV Hùng Vương Plaza (Tầng 7, 126 Hùng Vương, Q.5)\n"
                "• CGV Crescent Mall (Tầng 5, Phú Mỹ Hưng, Q.7)\n\n"
                "🌊 **Đà Nẵng**: CGV Vincom Plaza Ngô Quyền.\n"
                "📞 Hotline hỗ trợ chung: **1900 6017**"
            )

        if intent == "BOOK_TICKET":
            target_movie = movie['title'] if movie else 'bộ phim bạn yêu thích'
            return (
                f"🎟️ Để đặt vé xem phim **{target_movie}**, bạn có thể:\n"
                "1. Nhấn trực tiếp vào nút **'Đặt vé'** hoặc **'Xem suất chiếu'** trên thẻ phim ngay trong khung chat này.\n"
                "2. Chọn rạp, khung giờ và sơ đồ ghế ngồi yêu thích (Ghế thường, VIP hoặc Sweetbox cho 2 người).\n"
                "3. Hệ thống sẽ giữ chỗ và xác nhận vé ngay lập tức cho bạn!\n\n"
                "Bạn muốn đặt vé ở cụm rạp nào ạ?"
            )

        # Mặc định chung
        return (
            "Cimi đã hiểu yêu cầu của bạn! CGV luôn sẵn sàng mang đến cho bạn trải nghiệm điện ảnh tuyệt vời nhất. "
            "Bạn có muốn Cimi gợi ý danh sách phim đang chiếu hoặc kiểm tra lịch chiếu rạp gần nhất không?"
        )
